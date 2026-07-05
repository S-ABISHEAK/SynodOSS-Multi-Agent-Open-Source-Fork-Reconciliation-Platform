"""
policy_manager.py

Orchestrates the full policy lifecycle:
  Upload → Parse → Classify → Chunk → Embed → Persist

This is the entry point called by the API upload endpoint.
Handles idempotency via file content hash — unchanged files are not re-embedded.
"""
import hashlib
import logging
import tempfile
import os
from typing import Optional

from sqlalchemy.orm import Session

from src.models.schema import EnterprisePolicy, PolicyChunk, PolicyStatus
from src.services.policy.policy_parser import parse_policy_file
from src.services.policy.policy_classifier import classify_policy
from src.services.policy.policy_chunker import chunk_policy_text
from src.services.policy.policy_embedding import embed_texts

logger = logging.getLogger(__name__)


class PolicyManager:
    def __init__(self, db: Session):
        self.db = db

    def ingest_policy(
        self,
        file_bytes: bytes,
        filename: str,
        name: Optional[str] = None,
        version: str = "1.0",
        priority: str = "MEDIUM",
    ) -> EnterprisePolicy:
        """
        Full pipeline: parse → classify → chunk → embed → persist.

        Args:
            file_bytes: Raw bytes of the uploaded file.
            filename: Original filename (determines parser).
            name: Human-readable policy name (defaults to filename stem).
            version: Version string.
            priority: LOW | MEDIUM | HIGH | CRITICAL.

        Returns:
            The persisted EnterprisePolicy row.
        """
        # Step 0: Compute content hash for idempotency
        file_hash = hashlib.sha256(file_bytes).hexdigest()
        existing = self.db.query(EnterprisePolicy).filter_by(file_hash=file_hash).first()
        if existing:
            logger.info(f"[policy_manager] File already ingested — skipping (policy_id={existing.id})")
            return existing

        # Step 1: Write to temp file and parse
        with tempfile.NamedTemporaryFile(suffix=os.path.splitext(filename)[1], delete=False) as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name

        try:
            raw_text = parse_policy_file(tmp_path, filename)
        finally:
            os.unlink(tmp_path)

        if not raw_text or not raw_text.strip():
            raise ValueError(f"Could not extract any text from '{filename}'")

        # Step 2: Classify
        category = classify_policy(raw_text)

        # Step 3: Create EnterprisePolicy row
        policy_name = name or os.path.splitext(filename)[0].replace("_", " ").replace("-", " ").title()
        policy = EnterprisePolicy(
            name=policy_name,
            category=category,
            priority=priority,
            version=version,
            status=PolicyStatus.ACTIVE,
            file_name=filename,
            file_hash=file_hash,
        )
        self.db.add(policy)
        self.db.commit()
        self.db.refresh(policy)
        logger.info(f"[policy_manager] Created policy id={policy.id} name='{policy_name}' category={category.value}")

        # Step 4: Chunk
        chunks = chunk_policy_text(raw_text)
        non_duplicate_chunks = [c for c in chunks if not c.is_duplicate]
        logger.info(f"[policy_manager] {len(non_duplicate_chunks)} unique chunks to embed")

        # Step 5: Batch embed
        texts_to_embed = [c.chunk_text for c in non_duplicate_chunks]
        if texts_to_embed:
            embeddings = embed_texts(texts_to_embed)
        else:
            embeddings = []

        # Step 6: Persist chunks
        chunk_rows = []
        for chunk_data, embedding in zip(non_duplicate_chunks, embeddings):
            row = PolicyChunk(
                policy_id=policy.id,
                chunk_index=chunk_data.chunk_index,
                chunk_text=chunk_data.chunk_text,
                chunk_hash=chunk_data.chunk_hash,
                embedding=embedding,
                token_count=chunk_data.token_count,
            )
            chunk_rows.append(row)

        self.db.add_all(chunk_rows)
        policy.total_chunks = len(chunk_rows)
        self.db.commit()

        logger.info(
            f"[policy_manager] Ingested policy id={policy.id} "
            f"chunks={len(chunk_rows)} category={category.value}"
        )
        return policy

    def delete_policy(self, policy_id: int) -> bool:
        """Delete a policy and all its chunks."""
        policy = self.db.query(EnterprisePolicy).filter_by(id=policy_id).first()
        if not policy:
            return False
        self.db.query(PolicyChunk).filter_by(policy_id=policy_id).delete()
        self.db.delete(policy)
        self.db.commit()
        logger.info(f"[policy_manager] Deleted policy id={policy_id}")
        return True

    def list_policies(self) -> list[EnterprisePolicy]:
        return self.db.query(EnterprisePolicy).order_by(EnterprisePolicy.created_at.desc()).all()

    def get_policy(self, policy_id: int) -> Optional[EnterprisePolicy]:
        return self.db.query(EnterprisePolicy).filter_by(id=policy_id).first()

    def get_policy_chunks(self, policy_id: int) -> list[PolicyChunk]:
        return (
            self.db.query(PolicyChunk)
            .filter_by(policy_id=policy_id)
            .order_by(PolicyChunk.chunk_index)
            .all()
        )
