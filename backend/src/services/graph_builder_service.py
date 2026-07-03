"""
graph_builder_service.py — Stage 1 (graph_01.md)

Builds a deterministic, AST-based dependency graph for a repository.

Design principles:
- No LLMs. No regex symbol extraction. Pure AST only.
- Uses NetworkX for in-memory graph traversal.
- Persists GraphNode and GraphEdge rows to PostgreSQL.
- Idempotent: existing nodes are reused (no duplicates).
"""

import ast
import os
import logging
from pathlib import Path
from typing import Optional

import networkx as nx
from sqlalchemy.orm import Session

from src.models.schema import GraphNode, GraphEdge, NodeType, EdgeType

logger = logging.getLogger(__name__)

# File extensions supported by AST extraction
SUPPORTED_EXTENSIONS = {".py"}


class GraphBuilderService:
    def __init__(self, db: Session, base_dir: str = "data/repos"):
        self.db = db
        self.base_dir = os.path.abspath(base_dir)

    # ──────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────

    def build_graph(self, repository_id: int, scan_id: int, repo_path: str) -> nx.DiGraph:
        """
        Parse the entire repository, extract nodes and edges, persist them,
        and return an in-memory NetworkX DiGraph for traversal.

        Args:
            repository_id: DB id of the Repository row.
            scan_id: DB id of the RepositoryScan row (for snapshot versioning).
            repo_path: Absolute path to the cloned repository on disk.

        Returns:
            nx.DiGraph where nodes are (file_path, symbol_name) tuples and
            edges are labelled with EdgeType values.
        """
        graph = nx.DiGraph()
        node_db_map: dict[tuple[str, str], int] = {}  # (file_path, symbol) -> db id

        # --- Pass 1: Extract all nodes from all supported files ---
        py_files = self._find_python_files(repo_path)
        logger.info(f"[graph_builder] repo={repository_id} scan={scan_id} | found {len(py_files)} Python files")

        for file_path in py_files:
            relative_path = os.path.relpath(file_path, repo_path).replace("\\", "/")
            nodes = self._extract_nodes(file_path, relative_path)

            for node_data in nodes:
                db_node = self._get_or_create_node(
                    repository_id=repository_id,
                    scan_id=scan_id,
                    node_name=node_data["name"],
                    node_type=node_data["type"],
                    file_path=relative_path,
                    metadata=node_data.get("metadata", {}),
                )
                key = (relative_path, node_data["name"])
                node_db_map[key] = db_node.id
                graph.add_node(db_node.id, **{
                    "name": node_data["name"],
                    "node_type": node_data["type"].value,
                    "file_path": relative_path,
                })

        # --- Pass 2: Extract all edges ---
        for file_path in py_files:
            relative_path = os.path.relpath(file_path, repo_path).replace("\\", "/")
            edges = self._extract_edges(file_path, relative_path, node_db_map, repository_id)

            for src_id, tgt_id, edge_type in edges:
                if src_id == tgt_id:
                    continue
                # Avoid duplicate edges
                if not self.db.query(GraphEdge).filter_by(
                    source_node_id=src_id,
                    target_node_id=tgt_id,
                    edge_type=edge_type,
                ).first():
                    edge_row = GraphEdge(
                        source_node_id=src_id,
                        target_node_id=tgt_id,
                        edge_type=edge_type,
                    )
                    self.db.add(edge_row)
                graph.add_edge(src_id, tgt_id, edge_type=edge_type.value)

        self.db.commit()
        logger.info(
            f"[graph_builder] repo={repository_id} scan={scan_id} | "
            f"nodes={graph.number_of_nodes()} edges={graph.number_of_edges()}"
        )
        return graph

    def load_graph(self, repository_id: int, scan_id: Optional[int] = None) -> nx.DiGraph:
        """
        Reconstruct the NetworkX DiGraph from persisted DB rows.
        If scan_id is provided, loads only nodes from that snapshot.
        If scan_id is None, loads all nodes for the repository (legacy behaviour).
        """
        graph = nx.DiGraph()
        query = self.db.query(GraphNode).filter_by(repository_id=repository_id)
        if scan_id is not None:
            query = query.filter(GraphNode.scan_id == scan_id)
        nodes = query.all()
        for n in nodes:
            graph.add_node(n.id, name=n.node_name, node_type=n.node_type.value, file_path=n.file_path)

        node_ids = [n.id for n in nodes]
        if node_ids:
            edges = (
                self.db.query(GraphEdge)
                .filter(GraphEdge.source_node_id.in_(node_ids))
                .all()
            )
        else:
            edges = []
        for e in edges:
            graph.add_edge(e.source_node_id, e.target_node_id, edge_type=e.edge_type.value)

        return graph

    # ──────────────────────────────────────────────────────────────
    # Node Extraction
    # ──────────────────────────────────────────────────────────────

    def _extract_nodes(self, file_path: str, relative_path: str) -> list[dict]:
        """
        Parse a Python file and extract all symbol nodes:
        functions, async functions, classes.
        The module itself is also a node.
        """
        nodes: list[dict] = []

        # The file itself is a MODULE node
        module_name = relative_path.replace("/", ".").removesuffix(".py")
        nodes.append({
            "name": module_name,
            "type": NodeType.MODULE,
            "metadata": {"file_path": relative_path},
        })

        try:
            content = Path(file_path).read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(content)
        except (SyntaxError, OSError):
            return nodes

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                nodes.append({
                    "name": node.name,
                    "type": NodeType.CLASS,
                    "metadata": {
                        "lineno": node.lineno,
                        "end_lineno": getattr(node, "end_lineno", None),
                        "bases": [self._name_from_expr(b) for b in node.bases],
                    },
                })
                # Methods inside the class are FUNCTION nodes
                for child in ast.iter_child_nodes(node):
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        nodes.append({
                            "name": f"{node.name}.{child.name}",
                            "type": NodeType.FUNCTION,
                            "metadata": {
                                "lineno": child.lineno,
                                "end_lineno": getattr(child, "end_lineno", None),
                                "args": [a.arg for a in child.args.args],
                                "parent_class": node.name,
                            },
                        })
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Top-level function only (skip those already handled inside classes)
                # Check if parent is the Module
                nodes.append({
                    "name": node.name,
                    "type": NodeType.FUNCTION,
                    "metadata": {
                        "lineno": node.lineno,
                        "end_lineno": getattr(node, "end_lineno", None),
                        "args": [a.arg for a in node.args.args],
                    },
                })

        return nodes

    # ──────────────────────────────────────────────────────────────
    # Edge Extraction
    # ──────────────────────────────────────────────────────────────

    def _extract_edges(
        self,
        file_path: str,
        relative_path: str,
        node_db_map: dict[tuple[str, str], int],
        repository_id: int,
    ) -> list[tuple[int, int, EdgeType]]:
        """
        Walk the AST and produce (source_node_id, target_node_id, EdgeType) tuples.
        """
        edges: list[tuple[int, int, EdgeType]] = []

        try:
            content = Path(file_path).read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(content)
        except (SyntaxError, OSError):
            return edges

        module_name = relative_path.replace("/", ".").removesuffix(".py")
        module_key = (relative_path, module_name)
        module_id = node_db_map.get(module_key)

        for node in ast.walk(tree):
            # IMPORTS edges: module → imported_module
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                if module_id is None:
                    continue
                imported_names = self._resolve_import_names(node)
                for name in imported_names:
                    # Find target node (MODULE level)
                    target_id = self._find_node_id_by_name(name, repository_id)
                    if target_id and target_id != module_id:
                        edges.append((module_id, target_id, EdgeType.IMPORTS))

            # INHERITS edges: Class → BaseClass
            elif isinstance(node, ast.ClassDef):
                class_key = (relative_path, node.name)
                class_id = node_db_map.get(class_key)
                if class_id is None:
                    continue
                for base in node.bases:
                    base_name = self._name_from_expr(base)
                    if base_name:
                        base_id = self._find_node_id_by_name(base_name, repository_id)
                        if base_id and base_id != class_id:
                            edges.append((class_id, base_id, EdgeType.INHERITS))

            # CALLS edges: Function → Called Function
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                fn_key = (relative_path, node.name)
                fn_id = node_db_map.get(fn_key)
                if fn_id is None:
                    continue
                for child in ast.walk(node):
                    if isinstance(child, ast.Call):
                        called_name = self._name_from_expr(child.func)
                        if called_name:
                            target_id = self._find_node_id_by_name(called_name, repository_id)
                            if target_id and target_id != fn_id:
                                edges.append((fn_id, target_id, EdgeType.CALLS))

        return edges

    # ──────────────────────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────────────────────

    def _get_or_create_node(
        self,
        repository_id: int,
        scan_id: int,
        node_name: str,
        node_type: NodeType,
        file_path: str,
        metadata: dict,
    ) -> GraphNode:
        """Get existing node for this (repository, scan, file, name) or create a new one."""
        existing = self.db.query(GraphNode).filter_by(
            repository_id=repository_id,
            scan_id=scan_id,
            node_name=node_name,
            file_path=file_path,
        ).first()
        if existing:
            return existing
        node = GraphNode(
            repository_id=repository_id,
            scan_id=scan_id,
            node_name=node_name,
            node_type=node_type,
            file_path=file_path,
            node_metadata=metadata,
        )
        self.db.add(node)
        self.db.flush()  # Get the id without full commit
        return node

    def _find_node_id_by_name(self, name: str, repository_id: int) -> Optional[int]:
        """Look up a node by its symbol name within the repository."""
        row = self.db.query(GraphNode).filter_by(
            repository_id=repository_id,
            node_name=name,
        ).first()
        return row.id if row else None

    def _find_python_files(self, repo_path: str) -> list[str]:
        """Recursively find all .py files, skipping virtual environments and caches."""
        skip_dirs = {".venv", "venv", "__pycache__", ".git", "node_modules", "dist", "build"}
        result = []
        for root, dirs, files in os.walk(repo_path):
            dirs[:] = [d for d in dirs if d not in skip_dirs]
            for f in files:
                if f.endswith(".py"):
                    result.append(os.path.join(root, f))
        return result

    def _name_from_expr(self, node: ast.expr) -> Optional[str]:
        """Extract a string name from an AST expression (Name or Attribute)."""
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            val = self._name_from_expr(node.value)
            return f"{val}.{node.attr}" if val else node.attr
        return None

    def _resolve_import_names(self, node: ast.stmt) -> list[str]:
        """Return a flat list of top-level module names from an import statement."""
        names = []
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.append(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                names.append(node.module.split(".")[0])
        return names
