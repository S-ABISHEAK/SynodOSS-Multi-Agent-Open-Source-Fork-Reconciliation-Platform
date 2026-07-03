"""
knowledge_invalidation_service.py

Manages staleness and lifecycle of the repository knowledge layer:
- Marks FileSummary rows stale when a repo is re-scanned.
- Prunes old GraphNode/GraphEdge/FileSummary rows beyond a configurable
  retention window (default: keep last 3 scan snapshots per repository).

Called by the Celery worker (tasks.py):
  1. At the START of a new scan → mark old summaries stale.
  2. At the END of a successful scan → prune oldest snapshots.
"""

import logging
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from src.models.schema import (
    FileSummary,
    GraphEdge,
    GraphNode,
    RepositoryScan,
)

logger = logging.getLogger(__name__)

# Number of completed scan snapshots to keep per repository
DEFAULT_KEEP_LAST_N = 3


class KnowledgeInvalidationService:
    """
    Manages staleness and pruning of repository knowledge artifacts.
    """

    def __init__(self, db: Session):
        self.db = db

    # ──────────────────────────────────────────────────────────────
    # Invalidation
    # ──────────────────────────────────────────────────────────────

    def invalidate_scan(self, scan_id: int) -> int:
        """
        Mark all FileSummary rows for the given scan_id as stale.
        Called at the START of a new scan to ensure stale summaries from a
        prior run of this same scan (e.g. a retry) are not served.

        Returns the number of rows marked stale.
        """
        count = (
            self.db.query(FileSummary)
            .filter_by(scan_id=scan_id, is_stale=False)
            .update({"is_stale": True}, synchronize_session=False)
        )
        if count:
            self.db.commit()
            logger.info(f"[invalidation] scan={scan_id} marked {count} file summaries stale")
        return count

    def invalidate_file(self, scan_id: int, file_path: str) -> int:
        """
        Mark a single file's summary stale within a scan snapshot.
        Useful for partial invalidation when only specific files change.

        Returns the number of rows marked stale (0 or 1).
        """
        count = (
            self.db.query(FileSummary)
            .filter_by(scan_id=scan_id, file_path=file_path)
            .update({"is_stale": True}, synchronize_session=False)
        )
        if count:
            self.db.commit()
            logger.info(f"[invalidation] scan={scan_id} file={file_path} marked stale")
        return count

    def get_stale_files(self, scan_id: int) -> list[str]:
        """Return file paths with stale summaries in the given scan."""
        rows = (
            self.db.query(FileSummary.file_path)
            .filter_by(scan_id=scan_id, is_stale=True)
            .all()
        )
        return [r.file_path for r in rows]

    # ──────────────────────────────────────────────────────────────
    # Snapshot Pruning
    # ──────────────────────────────────────────────────────────────

    def cleanup_old_snapshots(
        self,
        repository_id: int,
        keep_last_n: int = DEFAULT_KEEP_LAST_N,
    ) -> dict[str, int]:
        """
        Delete GraphNode/GraphEdge/FileSummary rows for all but the most
        recent `keep_last_n` completed scans for the given repository.

        This prevents unbounded DB growth when a repo is scanned repeatedly.

        Returns a dict with counts of deleted rows per table.
        """
        # Find all scan IDs associated with this repository (as upstream or fork)
        all_scans = (
            self.db.query(RepositoryScan)
            .filter(
                (RepositoryScan.upstream_repo_id == repository_id)
                | (RepositoryScan.fork_repo_id == repository_id)
            )
            .order_by(RepositoryScan.id.desc())
            .all()
        )

        if len(all_scans) <= keep_last_n:
            logger.info(
                f"[invalidation] repo={repository_id} has {len(all_scans)} scans "
                f"(<= keep_last_n={keep_last_n}), nothing to prune"
            )
            return {"file_summaries": 0, "graph_nodes": 0, "graph_edges": 0}

        # Keep the N most recent; delete the rest
        scans_to_keep = {s.id for s in all_scans[:keep_last_n]}
        scans_to_delete = [s.id for s in all_scans[keep_last_n:]]

        logger.info(
            f"[invalidation] repo={repository_id} pruning {len(scans_to_delete)} old snapshots "
            f"(keeping scan_ids={sorted(scans_to_keep)})"
        )

        deleted: dict[str, int] = {
            "file_summaries": 0,
            "graph_nodes": 0,
            "graph_edges": 0,
        }

        try:
            # 1. Delete FileSummary rows for old scans
            deleted["file_summaries"] = (
                self.db.query(FileSummary)
                .filter(FileSummary.scan_id.in_(scans_to_delete))
                .delete(synchronize_session=False)
            )

            # 2. Find GraphNode IDs to delete (scoped to old scans)
            old_node_ids_query = (
                self.db.query(GraphNode.id)
                .filter(
                    GraphNode.repository_id == repository_id,
                    GraphNode.scan_id.in_(scans_to_delete),
                )
            )
            old_node_ids = [r.id for r in old_node_ids_query.all()]

            if old_node_ids:
                # 3. Delete GraphEdge rows referencing these nodes
                deleted["graph_edges"] = (
                    self.db.query(GraphEdge)
                    .filter(
                        (GraphEdge.source_node_id.in_(old_node_ids))
                        | (GraphEdge.target_node_id.in_(old_node_ids))
                    )
                    .delete(synchronize_session=False)
                )

                # 4. Delete the GraphNode rows themselves
                deleted["graph_nodes"] = (
                    self.db.query(GraphNode)
                    .filter(GraphNode.id.in_(old_node_ids))
                    .delete(synchronize_session=False)
                )

            self.db.commit()
            logger.info(
                f"[invalidation] repo={repository_id} pruned: "
                f"file_summaries={deleted['file_summaries']} "
                f"graph_nodes={deleted['graph_nodes']} "
                f"graph_edges={deleted['graph_edges']}"
            )

        except Exception as e:
            self.db.rollback()
            logger.error(f"[invalidation] repo={repository_id} pruning failed: {e}")
            raise

        return deleted
