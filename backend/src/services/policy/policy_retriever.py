"""
policy_retriever.py

Retrieves the top-K most relevant policy chunks for a given query text
using cosine similarity over stored embeddings.

Rules:
- Maximum 5 chunks returned.
- Skip retrieval if best similarity < MIN_SIMILARITY_THRESHOLD.
- Deduplicate overlapping chunks by chunk_hash.
- Results include similarity score and source policy metadata.
"""
import logging
from dataclasses import dataclass
from typing import Optional

from sqlalchemy.orm import Session

from src.models.schema import PolicyChunk, EnterprisePolicy, PolicyStatus
from src.services.policy.policy_embedding import embed_text, cosine_similarity

logger = logging.getLogger(__name__)

TOP_K = 5
MIN_SIMILARITY_THRESHOLD = 0.25


@dataclass
class RetrievedPolicyChunk:
    policy_id: int
    policy_name: str
    policy_category: str
    policy_priority: str
    chunk_id: int
    chunk_text: str
    similarity_score: float
    reason: str  # Why this chunk was selected


class PolicyRetriever:
    def __init__(self, db: Session):
        self.db = db

    def retrieve(self, query_text: str) -> list[RetrievedPolicyChunk]:
        """
        Retrieve the top-K most relevant policy chunks for a query.

        Args:
            query_text: The conflict context (diff + file summary) to search against.

        Returns:
            List of RetrievedPolicyChunk, sorted by similarity score descending.
        """
        if not query_text or not query_text.strip():
            return []

        # Get all active policy chunks with embeddings
        chunks = (
            self.db.query(PolicyChunk)
            .join(EnterprisePolicy, PolicyChunk.policy_id == EnterprisePolicy.id)
            .filter(EnterprisePolicy.status == PolicyStatus.ACTIVE)
            .filter(PolicyChunk.embedding.isnot(None))
            .all()
        )

        if not chunks:
            logger.info("[policy_retriever] No policy chunks with embeddings found")
            return []

        # Embed the query
        try:
            query_embedding = embed_text(query_text[:2000])  # cap query at 2000 chars
        except Exception as e:
            logger.error(f"[policy_retriever] Embedding failed: {e}")
            return []

        # Score all chunks
        scored: list[tuple[float, PolicyChunk]] = []
        for chunk in chunks:
            if not chunk.embedding:
                continue
            score = cosine_similarity(query_embedding, chunk.embedding)
            scored.append((score, chunk))

        # Sort by score descending
        scored.sort(key=lambda x: x[0], reverse=True)

        # Apply threshold and take top K
        results: list[RetrievedPolicyChunk] = []
        seen_hashes: set[str] = set()

        for score, chunk in scored[:TOP_K * 3]:  # over-fetch then filter
            if score < MIN_SIMILARITY_THRESHOLD:
                break
            if len(results) >= TOP_K:
                break
            # Deduplicate by chunk hash
            if chunk.chunk_hash and chunk.chunk_hash in seen_hashes:
                continue
            if chunk.chunk_hash:
                seen_hashes.add(chunk.chunk_hash)

            # Fetch parent policy metadata
            policy = self.db.query(EnterprisePolicy).filter(
                EnterprisePolicy.id == chunk.policy_id
            ).first()
            if not policy:
                continue

            results.append(RetrievedPolicyChunk(
                policy_id=policy.id,
                policy_name=policy.name,
                policy_category=policy.category.value if policy.category else "Unknown",
                policy_priority=policy.priority or "MEDIUM",
                chunk_id=chunk.id,
                chunk_text=chunk.chunk_text,
                similarity_score=round(score, 4),
                reason=_explain_relevance(score),
            ))

        logger.info(
            f"[policy_retriever] query_len={len(query_text)} "
            f"candidates={len(chunks)} retrieved={len(results)}"
        )
        return results


def _explain_relevance(score: float) -> str:
    """Generate a human-readable reason string for why this chunk was selected."""
    if score >= 0.70:
        return "Highly relevant — strong semantic overlap with the conflict context."
    elif score >= 0.50:
        return "Relevant — significant overlap detected with affected modules."
    elif score >= 0.35:
        return "Moderately relevant — partial match with conflict keywords."
    else:
        return "Weakly relevant — included as supporting context."
