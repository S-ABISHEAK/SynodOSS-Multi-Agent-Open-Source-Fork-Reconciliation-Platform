"""
retrieval_orchestrator_service.py

Assembles a bounded RetrievalBundle for a given ReconciliationUnit at debate time.
Queries the graph, file summaries, and impact data from the DB — never reads raw files.

Design:
- Token budget enforced at assembly time (TokenBudget limits).
- Graceful degradation: missing summaries or graph data produce partial bundles, not errors.
- The bundle's fields map 1-to-1 with the context dict expected by ConflictContextBuilder.
"""

import logging
from dataclasses import dataclass, field
from typing import Optional

from sqlalchemy.orm import Session

from src.models.schema import (
    FileSummary,
    GraphEdge,
    GraphNode,
    ImpactAnalysis,
    ReconciliationUnit,
)
from src.core.token_budget import TokenBudget

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# RetrievalBundle — the structured context payload passed to context_builder
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class RetrievalBundle:
    """
    A bounded, structured context payload assembled from the knowledge layer.
    Replaces raw file reads in ConflictContextBuilder.
    """
    file_path: str = ""
    symbol: str = ""
    symbol_type: str = "unknown"

    # Semantic summaries
    file_summary: str = ""
    related_file_summaries: dict = field(default_factory=dict)   # {file_path: summary_text}

    # Graph-derived context
    callers: list = field(default_factory=list)           # symbol names that call this symbol
    callees: list = field(default_factory=list)           # symbol names this symbol calls
    affected_functions: list = field(default_factory=list)
    affected_modules: list = field(default_factory=list)
    critical_paths: list = field(default_factory=list)
    dependency_depth: int = 0
    impact_score: float = 0.0

    # Architectural metadata
    architectural_layer: str = "Unknown"

    # Diff
    diff_preview: str = ""

    # Enterprise Policy context (EPACE)
    policy_context: str = ""                       # Formatted policy bundle for agent prompts
    retrieved_policy_chunks: list = field(default_factory=list)  # list[RetrievedPolicyChunk]
    policy_token_estimate: int = 0

    # Observability
    token_estimate: int = 0
    retrieval_source: str = "graph"   # "graph" | "fallback"

    def is_empty(self) -> bool:
        """Returns True if no useful knowledge was found (triggers fallback)."""
        return not self.file_summary and not self.callers and not self.callees

    def has_policy_context(self) -> bool:
        """Returns True if enterprise policy context was retrieved."""
        return bool(self.policy_context)


# ──────────────────────────────────────────────────────────────────────────────
# Service
# ──────────────────────────────────────────────────────────────────────────────

class RetrievalOrchestratorService:
    """
    Orchestrates retrieval from the knowledge layer for a given ReconciliationUnit.
    Called by ConflictContextBuilder at the start of each debate.
    """

    def __init__(self, db: Session):
        self.db = db

    def retrieve(self, unit: ReconciliationUnit) -> RetrievalBundle:
        """
        Build a bounded RetrievalBundle for the given unit.

        Retrieval order (mirrors rag_plan.md debate-time flow):
          1. File summary for the changed file
          2. GraphNode for the changed symbol (scan-scoped)
          3. Callers and callees from GraphEdge
          4. ImpactAnalysis (affected functions, modules, paths)
          5. File summaries for top related modules
          6. Apply token budget limits
        """
        bundle = RetrievalBundle(
            file_path=unit.file_path or "",
            symbol=unit.symbol or "unknown",
            symbol_type=unit.symbol_type or "unknown",
            diff_preview=unit.diff_hunk or "",
            architectural_layer=unit.architectural_layer or "Unknown",
            impact_score=unit.impact_score or 0.0,
            dependency_depth=unit.dependency_depth or 0,
            affected_functions=TokenBudget.rank_and_trim(
                unit.affected_functions or [], TokenBudget.MAX_AFFECTED_FUNCTIONS
            ),
            affected_modules=list(unit.affected_modules or []),
            critical_paths=TokenBudget.rank_and_trim(
                unit.critical_paths or [], TokenBudget.MAX_CRITICAL_PATHS
            ),
        )

        scan_id = unit.scan_id

        # Step 1: File summary for changed file
        bundle.file_summary = self._get_file_summary(scan_id, unit.file_path)

        # Step 2 & 3: Graph callers and callees
        if unit.symbol:
            callers, callees = self._get_callers_callees(scan_id, unit.symbol)
            bundle.callers = TokenBudget.rank_and_trim(callers, TokenBudget.MAX_CALLERS)
            bundle.callees = TokenBudget.rank_and_trim(callees, TokenBudget.MAX_CALLERS)

        # Step 4: Enrich from ImpactAnalysis table if available
        bundle = self._enrich_from_impact_analysis(unit.id, bundle)

        # Step 5: Related file summaries (for affected modules)
        bundle.related_file_summaries = self._get_related_summaries(
            scan_id, bundle.affected_modules
        )

        # Step 6: Apply token budget to text fields
        bundle.diff_preview = TokenBudget.truncate_to_budget(
            bundle.diff_preview, TokenBudget.MAX_TOKENS_DIFF, label="diff"
        )
        bundle.file_summary = TokenBudget.truncate_to_budget(
            bundle.file_summary, TokenBudget.MAX_TOKENS_FILE_SUMMARY, label="file_summary"
        )

        # Step 7: Retrieve enterprise policy context (EPACE)
        bundle = self._attach_policy_context(bundle)

        # Compute total token estimate for observability
        bundle.token_estimate = self._estimate_bundle_tokens(bundle)
        bundle.retrieval_source = "graph" if not bundle.is_empty() else "fallback"

        logger.info(
            f"[retrieval] unit={unit.id} file={unit.file_path} symbol={unit.symbol} "
            f"| callers={len(bundle.callers)} callees={len(bundle.callees)} "
            f"| related_files={len(bundle.related_file_summaries)} "
            f"| token_estimate={bundle.token_estimate} source={bundle.retrieval_source}"
        )

        return bundle

    # ──────────────────────────────────────────────────────────────
    # Internal retrieval helpers
    # ──────────────────────────────────────────────────────────────

    def _get_file_summary(self, scan_id: int, file_path: Optional[str]) -> str:
        """Fetch file summary text for (scan_id, file_path). Returns '' if not found."""
        if not file_path:
            return ""
        row = (
            self.db.query(FileSummary)
            .filter_by(scan_id=scan_id, file_path=file_path, is_stale=False)
            .first()
        )
        return row.summary_text if row else ""

    def _get_callers_callees(
        self, scan_id: int, symbol_name: str
    ) -> tuple[list[str], list[str]]:
        """
        Find all symbols that CALL the given symbol (callers) and
        all symbols the given symbol CALLS (callees) within the scan snapshot.
        """
        # Find the GraphNode for this symbol in this scan
        node = (
            self.db.query(GraphNode)
            .filter(GraphNode.scan_id == scan_id, GraphNode.node_name == symbol_name)
            .first()
        )
        if not node:
            return [], []

        # Callers: edges where target = this node
        caller_edges = (
            self.db.query(GraphEdge)
            .filter(GraphEdge.target_node_id == node.id)
            .limit(TokenBudget.MAX_CALLERS * 2)  # over-fetch, then trim
            .all()
        )
        caller_ids = [e.source_node_id for e in caller_edges]
        callers = self._node_names_for_ids(caller_ids)

        # Callees: edges where source = this node
        callee_edges = (
            self.db.query(GraphEdge)
            .filter(GraphEdge.source_node_id == node.id)
            .limit(TokenBudget.MAX_CALLERS * 2)
            .all()
        )
        callee_ids = [e.target_node_id for e in callee_edges]
        callees = self._node_names_for_ids(callee_ids)

        return callers, callees

    def _node_names_for_ids(self, node_ids: list[int]) -> list[str]:
        """Batch-fetch node names for a list of GraphNode IDs."""
        if not node_ids:
            return []
        nodes = (
            self.db.query(GraphNode)
            .filter(GraphNode.id.in_(node_ids))
            .all()
        )
        return [n.node_name for n in nodes]

    def _enrich_from_impact_analysis(
        self, unit_id: int, bundle: RetrievalBundle
    ) -> RetrievalBundle:
        """
        Supplement bundle with persisted ImpactAnalysis data if available.
        ImpactAnalysis has more accurate blast-radius data than the unit columns.
        """
        ia = (
            self.db.query(ImpactAnalysis)
            .filter_by(reconciliation_unit_id=unit_id)
            .first()
        )
        if not ia:
            return bundle

        # Use ImpactAnalysis data when it's more complete
        if ia.affected_functions and len(ia.affected_functions) > len(bundle.affected_functions):
            bundle.affected_functions = TokenBudget.rank_and_trim(
                ia.affected_functions, TokenBudget.MAX_AFFECTED_FUNCTIONS
            )
        if ia.affected_modules and len(ia.affected_modules) > len(bundle.affected_modules):
            bundle.affected_modules = list(ia.affected_modules)
        if ia.critical_paths and len(ia.critical_paths) > len(bundle.critical_paths):
            bundle.critical_paths = TokenBudget.rank_and_trim(
                ia.critical_paths, TokenBudget.MAX_CRITICAL_PATHS
            )
        if ia.impact_score and ia.impact_score > 0:
            bundle.impact_score = ia.impact_score
        if ia.dependency_depth and ia.dependency_depth > 0:
            bundle.dependency_depth = ia.dependency_depth

        return bundle

    def _get_related_summaries(
        self, scan_id: int, affected_modules: list[str]
    ) -> dict[str, str]:
        """
        Fetch file summaries for modules in the blast radius.
        Module names are converted to probable file paths for lookup.
        Limited to MAX_RELATED_FILES entries.
        """
        if not affected_modules:
            return {}

        # Attempt a direct name match against file_path field
        trimmed_modules = affected_modules[: TokenBudget.MAX_RELATED_FILES * 3]
        rows = (
            self.db.query(FileSummary)
            .filter(
                FileSummary.scan_id == scan_id,
                FileSummary.is_stale == False,  # noqa: E712
            )
            .all()
        )

        result: dict[str, str] = {}
        for row in rows:
            # Match if the module name appears in the file path
            for mod in trimmed_modules:
                mod_clean = mod.replace(".", "/")
                if mod_clean in row.file_path or mod in row.file_path:
                    if len(result) < TokenBudget.MAX_RELATED_FILES:
                        summary = TokenBudget.truncate_to_budget(
                            row.summary_text,
                            TokenBudget.MAX_TOKENS_FILE_SUMMARY,
                            label=row.file_path,
                        )
                        result[row.file_path] = summary
                    break

        return result

    def _attach_policy_context(self, bundle: RetrievalBundle) -> RetrievalBundle:
        """Retrieve and attach enterprise policy context to the bundle."""
        try:
            from src.services.policy.policy_retriever import PolicyRetriever
            from src.services.policy.policy_context_builder import build_policy_context

            # Build a query from the diff + file summary (most relevant signals)
            query = f"{bundle.diff_preview[:500]} {bundle.file_summary[:300]}".strip()
            if not query:
                return bundle

            retriever = PolicyRetriever(self.db)
            chunks = retriever.retrieve(query)
            policy_bundle = build_policy_context(chunks)

            bundle.retrieved_policy_chunks = chunks
            bundle.policy_context = policy_bundle.formatted_context
            bundle.policy_token_estimate = policy_bundle.total_token_estimate

            if chunks:
                logger.info(
                    f"[retrieval] policy_chunks={len(chunks)} "
                    f"policy_tokens={bundle.policy_token_estimate}"
                )
        except Exception as e:
            logger.warning(f"[retrieval] Policy context retrieval failed (non-fatal): {e}")
        return bundle

    def _estimate_bundle_tokens(self, bundle: RetrievalBundle) -> int:
        """Estimate total token count of the bundle for observability logging."""
        parts = [
            bundle.file_summary,
            bundle.diff_preview,
            " ".join(bundle.callers),
            " ".join(bundle.callees),
            " ".join(bundle.affected_functions),
            " ".join(bundle.affected_modules),
            " ".join(str(p) for p in bundle.critical_paths),
            " ".join(bundle.related_file_summaries.values()),
            bundle.policy_context,
        ]
        return sum(TokenBudget.estimate_tokens(p) for p in parts)
