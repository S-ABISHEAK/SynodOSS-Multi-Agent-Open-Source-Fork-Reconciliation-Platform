import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from src.models.schema import DecisionRecord, GraphNode, Commit, Conflict

logger = logging.getLogger(__name__)

class RepositoryKnowledgeStore:
    """
    Long-term knowledge store interacting with PostgreSQL.
    Stores and retrieves past decisions, known architectural conflicts, and symbol locations.
    Replaces the "start from scratch" debate model.
    """
    def __init__(self, db: Session):
        self.db = db

    def retrieve_symbol_context(self, repository_id: int, symbol_name: str) -> Optional[Dict[str, Any]]:
        """Retrieve historical knowledge about a specific symbol."""
        node = self.db.query(GraphNode).filter_by(repository_id=repository_id, node_name=symbol_name).first()
        if not node:
            return None
            
        return {
            "node_type": node.node_type.value,
            "file_path": node.file_path,
            "metadata": node.node_metadata
        }

    def retrieve_past_decisions(self, file_path: str, limit: int = 3) -> List[Dict[str, Any]]:
        """Retrieve previous architect decisions made for a given file to ensure consistency."""
        conflicts = self.db.query(Conflict).filter_by(file_path=file_path).all()
        conflict_ids = [c.id for c in conflicts]
        
        if not conflict_ids:
            return []
            
        decisions = self.db.query(DecisionRecord).filter(DecisionRecord.conflict_id.in_(conflict_ids)).order_by(DecisionRecord.created_at.desc()).limit(limit).all()
        
        results = []
        for d in decisions:
            results.append({
                "decision": d.architect_decision,
                "created_at": d.created_at.isoformat(),
                "evidence": d.evidence
            })
        return results

    def store_decision(self, conflict_id: int, architect_decision: str, evidence: List[Dict[str, Any]], verification_result: Dict[str, Any]) -> DecisionRecord:
        """Store the outcome of a debate."""
        record = DecisionRecord(
            conflict_id=conflict_id,
            architect_decision=architect_decision,
            evidence=evidence,
            verification_result=verification_result
        )
        self.db.add(record)
        self.db.commit()
        return record
