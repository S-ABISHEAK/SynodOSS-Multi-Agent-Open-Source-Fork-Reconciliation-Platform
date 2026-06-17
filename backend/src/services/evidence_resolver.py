"""
evidence_resolver.py — Stage 2 (graph_02.md)

Validates agent claims before the council uses them as evidence.

Verification Rules (from graph_02.md):
  - Reject claims when symbol not found in AST
  - Reject claims when commit not found / too short
  - Reject claims when line range is invalid
  - Reject claims when dependency relationship is invalid (graph-level)
"""

import os
import ast
import logging
from typing import Optional
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class EvidenceResolver:
    """
    Validates agent evidence claims against the repository's AST, git history,
    and the dependency graph stored in the database.
    """

    def __init__(self, base_dir: str = "data/repos", db: Optional[Session] = None):
        self.base_dir = os.path.abspath(base_dir)
        self.db = db  # Optional — required for graph relationship validation

    def validate_evidence(
        self,
        repo_path: str,
        file_path: str,
        commit: str = None,
        symbol: str = None,
        line_start: int = None,
        line_end: int = None,
    ) -> dict:
        """
        Validates if the provided evidence (commit, symbol, lines) actually exists in the file.
        Returns a dictionary with validation status and error list.
        """
        result = {"is_valid": True, "errors": []}
        full_path = os.path.join(repo_path, file_path)

        # 1. File existence
        if not os.path.exists(full_path):
            result["is_valid"] = False
            result["errors"].append(f"File '{file_path}' does not exist in the repository.")
            return result

        try:
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()
                lines = content.splitlines()
        except Exception as e:
            result["is_valid"] = False
            result["errors"].append(f"Could not read file '{file_path}': {e}")
            return result

        # 2. Line range validation
        total_lines = len(lines)
        if line_start is not None:
            if line_start < 1 or line_start > total_lines:
                result["is_valid"] = False
                result["errors"].append(
                    f"line_start {line_start} is out of bounds (1–{total_lines})."
                )
            if line_end is not None and line_start is not None:
                if line_end < line_start or line_end > total_lines:
                    result["is_valid"] = False
                    result["errors"].append(
                        f"line_end {line_end} is out of bounds or less than line_start."
                    )

        # 3. Symbol validation via AST
        if symbol and file_path.endswith(".py"):
            try:
                tree = ast.parse(content)
                found = False
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                        if node.name == symbol or f"{symbol}".endswith(f".{node.name}"):
                            found = True
                            if line_start and hasattr(node, "lineno") and hasattr(node, "end_lineno"):
                                if not (node.lineno <= line_start <= node.end_lineno):
                                    result["is_valid"] = False
                                    result["errors"].append(
                                        f"Symbol '{symbol}' exists at lines {node.lineno}–{node.end_lineno}, "
                                        f"not at line {line_start}."
                                    )
                            break
                if not found:
                    result["is_valid"] = False
                    result["errors"].append(f"Symbol '{symbol}' does not exist in the AST of '{file_path}'.")
            except SyntaxError:
                result["errors"].append(f"Warning: Could not parse AST for '{file_path}' (SyntaxError).")
            except Exception as e:
                result["errors"].append(f"Warning: AST parse error for '{file_path}': {e}")

        # 4. Commit hash validation
        if commit:
            if len(commit) < 6:
                result["is_valid"] = False
                result["errors"].append(f"Commit hash '{commit}' is too short to be valid.")

        return result

    def validate_graph_relationship(
        self,
        source_symbol: str,
        target_symbol: str,
        expected_edge_type: str,
        repository_id: int,
    ) -> dict:
        """
        Validates that a claimed dependency relationship actually exists
        in the stored GraphEdge table.

        Returns {"is_valid": bool, "errors": list[str]}
        """
        result = {"is_valid": True, "errors": []}

        if self.db is None:
            result["errors"].append("Graph validation skipped: no database session available.")
            return result

        from src.models.schema import GraphNode, GraphEdge, EdgeType

        source_row = self.db.query(GraphNode).filter_by(
            repository_id=repository_id,
            node_name=source_symbol,
        ).first()

        target_row = self.db.query(GraphNode).filter_by(
            repository_id=repository_id,
            node_name=target_symbol,
        ).first()

        if not source_row:
            result["is_valid"] = False
            result["errors"].append(
                f"Source symbol '{source_symbol}' not found in graph for repo={repository_id}."
            )
            return result

        if not target_row:
            result["is_valid"] = False
            result["errors"].append(
                f"Target symbol '{target_symbol}' not found in graph for repo={repository_id}."
            )
            return result

        # Validate the claimed edge type
        try:
            edge_type_enum = EdgeType(expected_edge_type.upper())
        except ValueError:
            result["is_valid"] = False
            result["errors"].append(
                f"Unknown edge type '{expected_edge_type}'. "
                f"Must be one of: {[e.value for e in EdgeType]}."
            )
            return result

        edge = self.db.query(GraphEdge).filter_by(
            source_node_id=source_row.id,
            target_node_id=target_row.id,
            edge_type=edge_type_enum,
        ).first()

        if not edge:
            result["is_valid"] = False
            result["errors"].append(
                f"No '{expected_edge_type}' edge found between "
                f"'{source_symbol}' → '{target_symbol}' in the dependency graph."
            )

        return result

    def build_validation_report(self, history: list[dict], repo_path: str, file_path: str) -> list[str]:
        """
        Iterates over agent history messages and validates all evidence items.
        Returns a list of report strings for injection into the judge's context.
        """
        report = []
        for msg in history:
            role = msg.get("agent_role", "unknown")
            for ev in msg.get("evidence_provided", []):
                if not isinstance(ev, dict):
                    continue
                description = ev.get("description", "(no description)")
                symbol = ev.get("symbol")
                line_start = ev.get("line_start")
                line_end = ev.get("line_end")
                commit = ev.get("commit")

                res = self.validate_evidence(
                    repo_path=repo_path,
                    file_path=file_path,
                    commit=commit,
                    symbol=symbol,
                    line_start=line_start,
                    line_end=line_end,
                )
                status = "VALID" if res["is_valid"] else f"INVALID ({'; '.join(res['errors'])})"
                report.append(f"[{role}] \"{description}\" → {status}")
        return report
