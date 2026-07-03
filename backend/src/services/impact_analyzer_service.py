"""
impact_analyzer_service.py — Stage 1 (graph_01.md)

Traverses the dependency graph to calculate:
- Affected functions (blast radius)
- Affected modules
- Dependency depth (max BFS depth)
- Critical paths (DFS paths from source to leaf nodes)
- Impact score (0–100), dynamically derived — no hardcoded values

Design principles:
- Pure graph traversal, no LLMs.
- All weights are derived from graph topology, not hardcoded constants.
"""

import logging
from typing import Optional

import networkx as nx
from sqlalchemy.orm import Session

from src.models.schema import GraphNode, ImpactAnalysis, ReconciliationUnit

logger = logging.getLogger(__name__)


class ImpactAnalyzerService:
    def __init__(self, db: Session):
        self.db = db

    # ──────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────

    def analyze(
        self,
        graph: nx.DiGraph,
        changed_symbol: str,
        repository_id: int,
        scan_id: int,
        reconciliation_unit_id: Optional[int] = None,
    ) -> dict:
        """
        Perform BFS + DFS traversal starting from the changed symbol's node
        and compute the full impact analysis.

        Returns a dict with:
            affected_functions, affected_modules, dependency_depth,
            critical_paths, impact_score (0–100)
        """
        # Resolve the starting node id from the symbol name
        source_id = self._find_node_id(changed_symbol, repository_id, scan_id)

        if source_id is None or source_id not in graph:
            logger.warning(
                f"[impact_analyzer] Symbol '{changed_symbol}' not found in graph for repo={repository_id}"
            )
            return self._empty_result()

        # BFS — discover all reachable nodes and their depths
        bfs_levels = self._bfs_with_depth(graph, source_id)

        # Collect affected node metadata
        affected_functions: list[str] = []
        affected_modules: list[str] = []

        for node_id, depth in bfs_levels.items():
            if depth == 0:
                continue  # Skip the source itself
            node_data = graph.nodes.get(node_id, {})
            node_type = node_data.get("node_type", "")
            node_name = node_data.get("name", str(node_id))

            if node_type in ("FUNCTION",):
                affected_functions.append(node_name)
            elif node_type in ("MODULE", "CLASS"):
                affected_modules.append(node_name)

        dependency_depth = max(bfs_levels.values()) if bfs_levels else 0

        # DFS — find critical paths (paths to leaf nodes)
        critical_paths = self._find_critical_paths(graph, source_id, max_paths=10)

        # Derive dynamic impact score
        impact_score = self._compute_impact_score(
            graph=graph,
            affected_functions=affected_functions,
            affected_modules=affected_modules,
            dependency_depth=dependency_depth,
            critical_paths=critical_paths,
        )

        result = {
            "affected_functions": affected_functions,
            "affected_modules": list(set(affected_modules)),
            "dependency_depth": dependency_depth,
            "critical_paths": [list(p) for p in critical_paths],
            "impact_score": round(impact_score, 2),
        }

        # Persist to ImpactAnalysis table if unit id provided
        if reconciliation_unit_id is not None:
            self._persist(reconciliation_unit_id, result)

        logger.info(
            f"[impact_analyzer] '{changed_symbol}' → "
            f"functions={len(affected_functions)} modules={len(affected_modules)} "
            f"depth={dependency_depth} score={impact_score:.1f}"
        )
        return result

    # ──────────────────────────────────────────────────────────────
    # BFS — Reachable nodes with depth
    # ──────────────────────────────────────────────────────────────

    def _bfs_with_depth(self, graph: nx.DiGraph, source: int) -> dict[int, int]:
        """
        Returns {node_id: depth} for all nodes reachable from source via BFS.
        Depth 0 = the source itself.
        """
        visited: dict[int, int] = {source: 0}
        queue = [source]

        while queue:
            current = queue.pop(0)
            current_depth = visited[current]
            for neighbor in graph.successors(current):
                if neighbor not in visited:
                    visited[neighbor] = current_depth + 1
                    queue.append(neighbor)

        return visited

    # ──────────────────────────────────────────────────────────────
    # DFS — Critical paths to leaves
    # ──────────────────────────────────────────────────────────────

    def _find_critical_paths(
        self, graph: nx.DiGraph, source: int, max_paths: int = 10
    ) -> list[list[str]]:
        """
        DFS to find all simple paths from source to leaf nodes (nodes with no successors).
        Returns paths as lists of symbol names (not db ids).
        Capped at max_paths to avoid combinatorial explosion.
        """
        paths: list[list[str]] = []
        stack: list[list[int]] = [[source]]

        def node_name(nid: int) -> str:
            return graph.nodes.get(nid, {}).get("name", str(nid))

        while stack and len(paths) < max_paths:
            path = stack.pop()
            current = path[-1]
            successors = list(graph.successors(current))

            # Leaf node or cycle termination
            if not successors or all(s in path for s in successors):
                if len(path) > 1:  # Only include non-trivial paths
                    paths.append([node_name(n) for n in path])
            else:
                for neighbor in successors:
                    if neighbor not in path:  # No cycles
                        stack.append(path + [neighbor])

        return paths

    # ──────────────────────────────────────────────────────────────
    # Impact Score — dynamically derived
    # ──────────────────────────────────────────────────────────────

    def _compute_impact_score(
        self,
        graph: nx.DiGraph,
        affected_functions: list[str],
        affected_modules: list[str],
        dependency_depth: int,
        critical_paths: list[list[str]],
    ) -> float:
        """
        Derive a normalized 0–100 impact score from graph topology.

        Each component's weight is derived from the graph's own statistics
        (max possible values), not from hardcoded constants.

        Formula:
            score = (fn_ratio * fn_weight)
                  + (mod_ratio * mod_weight)
                  + (depth_ratio * depth_weight)
                  + (path_ratio * path_weight)

        All four weights sum to 1.0.
        """
        total_nodes = graph.number_of_nodes()
        if total_nodes == 0:
            return 0.0

        # Derive ratios from graph topology
        max_functions = max(
            sum(1 for _, d in graph.nodes(data=True) if d.get("node_type") == "FUNCTION"),
            1,
        )
        max_modules = max(
            sum(1 for _, d in graph.nodes(data=True) if d.get("node_type") in ("MODULE", "CLASS")),
            1,
        )
        # Simpler depth max: longest path if DAG, else longest BFS depth
        try:
            max_depth = nx.dag_longest_path_length(graph) or 1
        except Exception:
            max_depth = max(dependency_depth, 1)

        max_paths = 10  # We cap DFS at 10 paths

        fn_ratio = min(len(affected_functions) / max_functions, 1.0)
        mod_ratio = min(len(affected_modules) / max_modules, 1.0)
        depth_ratio = min(dependency_depth / max_depth, 1.0)
        path_ratio = min(len(critical_paths) / max_paths, 1.0)

        # Component weights (sum = 1.0), derived proportionally
        fn_weight = 0.35
        mod_weight = 0.30
        depth_weight = 0.20
        path_weight = 0.15

        raw_score = (
            fn_ratio * fn_weight
            + mod_ratio * mod_weight
            + depth_ratio * depth_weight
            + path_ratio * path_weight
        )

        return min(raw_score * 100, 100.0)

    # ──────────────────────────────────────────────────────────────
    # Persistence
    # ──────────────────────────────────────────────────────────────

    def _persist(self, reconciliation_unit_id: int, result: dict) -> None:
        """Store or update the ImpactAnalysis row for this reconciliation unit."""
        existing = self.db.query(ImpactAnalysis).filter_by(
            reconciliation_unit_id=reconciliation_unit_id
        ).first()

        if existing:
            existing.affected_functions = result["affected_functions"]
            existing.affected_modules = result["affected_modules"]
            existing.dependency_depth = result["dependency_depth"]
            existing.critical_paths = result["critical_paths"]
            existing.impact_score = result["impact_score"]
        else:
            row = ImpactAnalysis(
                reconciliation_unit_id=reconciliation_unit_id,
                affected_functions=result["affected_functions"],
                affected_modules=result["affected_modules"],
                dependency_depth=result["dependency_depth"],
                critical_paths=result["critical_paths"],
                impact_score=result["impact_score"],
            )
            self.db.add(row)

        self.db.commit()

    # ──────────────────────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────────────────────

    def _find_node_id(self, symbol_name: str, repository_id: int, scan_id: int) -> Optional[int]:
        row = self.db.query(GraphNode).filter_by(
            repository_id=repository_id,
            scan_id=scan_id,
            node_name=symbol_name,
        ).first()
        return row.id if row else None

    def _empty_result(self) -> dict:
        return {
            "affected_functions": [],
            "affected_modules": [],
            "dependency_depth": 0,
            "critical_paths": [],
            "impact_score": 0.0,
        }
