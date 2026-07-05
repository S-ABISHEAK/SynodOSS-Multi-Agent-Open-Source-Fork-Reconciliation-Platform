import os
import ast
import re
import subprocess
import logging
from pathlib import Path
from src.models.schema import ReconciliationUnit
from src.core.token_budget import TokenBudget

logger = logging.getLogger(__name__)

# Base path where repos are cloned
REPOS_BASE = Path(__file__).parent.parent.parent / "data" / "repos"


class ConflictContextBuilder:
    def build_context(self, unit: ReconciliationUnit) -> dict:
        """
        Builds a rich, grounded context dict for the agents.

        Primary path: queries the knowledge layer (FileSummary, GraphNode,
        GraphEdge, ImpactAnalysis) via RetrievalOrchestratorService to assemble
        a compact, token-budgeted evidence bundle.

        Fallback path: if no knowledge layer data exists yet (e.g. first scan
        before FileSummaryService has run), falls back to the original AST +
        raw-file read approach so the debate still works.

        The returned dict shape is identical to the previous version — no
        downstream changes required in debate_manager or agent_manager.
        """
        scan_id = unit.scan_id
        file_path = unit.file_path

        # ── Primary path: Retrieval Orchestrator ────────────────────
        bundle = self._try_retrieval(unit)

        if bundle is not None and not bundle.is_empty():
            logger.info(
                f"[context_builder] unit={unit.id} Using knowledge-layer retrieval "
                f"(token_estimate={bundle.token_estimate})"
            )
            return self._context_from_bundle(unit, bundle)

        # ── Fallback path: raw file reads + AST ─────────────────────
        logger.info(
            f"[context_builder] unit={unit.id} No retrieval data found — "
            "falling back to raw file reads"
        )
        return self._context_from_raw(unit, scan_id, file_path)

    # ──────────────────────────────────────────────────────────────
    # Primary: Knowledge-Layer Path
    # ──────────────────────────────────────────────────────────────

    def _try_retrieval(self, unit: ReconciliationUnit):
        """
        Attempt to build a RetrievalBundle from the knowledge layer.
        Returns None if the retrieval service is unavailable or errors out.
        """
        try:
            from src.core.database import SessionLocal
            from src.services.retrieval_orchestrator_service import RetrievalOrchestratorService
            db = SessionLocal()
            try:
                svc = RetrievalOrchestratorService(db)
                return svc.retrieve(unit)
            finally:
                db.close()
        except Exception as e:
            logger.warning(f"[context_builder] Retrieval orchestrator failed: {e}")
            return None

    def _context_from_bundle(self, unit: ReconciliationUnit, bundle) -> dict:
        """Build the context dict from a RetrievalBundle."""
        # Fetch commit messages (fast git log, no file reading)
        upstream_commit_messages = self._get_commit_messages(
            unit.scan_id, "upstream", unit.upstream_commits or []
        )
        fork_commit_messages = self._get_commit_messages(
            unit.scan_id, "fork", unit.fork_commits or []
        )

        # Apply token budget to commit message block
        commit_block = "\n".join(upstream_commit_messages + fork_commit_messages)
        commit_block = TokenBudget.truncate_to_budget(
            commit_block, TokenBudget.MAX_TOKENS_COMMIT_MSG, label="commit_messages"
        )

        # Build compressed_context from bundle (replaces ContextCompressionService)
        compressed_context = {
            "symbol": bundle.symbol,
            "type": bundle.symbol_type,
            "callers": len(bundle.callers),
            "callees": len(bundle.callees),
            "caller_names": bundle.callers,
            "callee_names": bundle.callees,
            "affected_modules": len(bundle.affected_modules),
            "dependency_depth": bundle.dependency_depth,
            "changed_signature": bundle.symbol in (unit.symbol or ""),
            "security_impact": self._infer_security_impact(bundle.file_path),
            "affected_functions": len(bundle.affected_functions),
            "impact_score": bundle.impact_score,
            "file_summary": bundle.file_summary,
            "related_files": bundle.related_file_summaries,
        }

        # Log token budget report for observability
        sections = {
            "diff": bundle.diff_preview,
            "file_summary": bundle.file_summary,
            "callers": " ".join(bundle.callers),
            "callees": " ".join(bundle.callees),
            "related_files": " ".join(bundle.related_file_summaries.values()),
            "commit_messages": commit_block,
        }
        budget_report = TokenBudget.budget_report(sections)
        logger.info(f"[context_builder] token budget report: {budget_report}")

        return {
            "file_path": bundle.file_path,
            "complexity_score": unit.complexity_score,
            "diff_preview": bundle.diff_preview,
            "upstream_commit_messages": upstream_commit_messages,
            "fork_commit_messages": fork_commit_messages,
            "ast_summary": {"summary": f"Knowledge layer retrieval — {bundle.symbol}"},
            "compressed_context": compressed_context,
            # Graph-aware impact fields (same keys as before)
            "changed_symbol": bundle.symbol,
            "impact_score": bundle.impact_score,
            "affected_functions": bundle.affected_functions,
            "affected_modules": bundle.affected_modules,
            "critical_paths": bundle.critical_paths,
            "dependency_depth": bundle.dependency_depth,
            "architectural_layer": bundle.architectural_layer,
            # EPACE: Enterprise policy context injected into agent prompts
            "enterprise_policies": bundle.policy_context,
            "_retrieved_policy_chunks": bundle.retrieved_policy_chunks,  # for PolicyAnalyzer (internal)
        }

    # ──────────────────────────────────────────────────────────────
    # Fallback: Raw File Read + AST Path
    # ──────────────────────────────────────────────────────────────

    def _context_from_raw(
        self, unit: ReconciliationUnit, scan_id: int, file_path: str
    ) -> dict:
        """
        Original context building approach — reads raw files, runs AST summary.
        Used when the knowledge layer has no data yet (e.g. first scan).
        """
        upstream_content = self._read_file(scan_id, "upstream", file_path)
        fork_content = self._read_file(scan_id, "fork", file_path)

        upstream_commit_messages = self._get_commit_messages(
            scan_id, "upstream", unit.upstream_commits or []
        )
        fork_commit_messages = self._get_commit_messages(
            scan_id, "fork", unit.fork_commits or []
        )

        ast_summary = self._build_ast_summary(upstream_content, fork_content, file_path)
        diff_preview = unit.diff_hunk or "(no diff available)"

        # Keep ContextCompressionService for the fallback path
        from src.services.context_compression_service import ContextCompressionService
        compressor = ContextCompressionService()
        compressed_context = compressor.compress(unit)

        return {
            "file_path": file_path,
            "complexity_score": unit.complexity_score,
            "diff_preview": diff_preview,
            "upstream_commit_messages": upstream_commit_messages,
            "fork_commit_messages": fork_commit_messages,
            "ast_summary": ast_summary,
            "compressed_context": compressed_context,
            "changed_symbol": unit.symbol or "Unknown",
            "impact_score": unit.impact_score or 0.0,
            "affected_functions": unit.affected_functions or [],
            "affected_modules": unit.affected_modules or [],
            "critical_paths": unit.critical_paths or [],
            "dependency_depth": unit.dependency_depth or 0,
            "architectural_layer": unit.architectural_layer or "Unknown",
        }

    # ──────────────────────────────────────────────────────────────
    # File Reading (fallback only)
    # ──────────────────────────────────────────────────────────────

    def _read_file(self, scan_id: int, repo_type: str, file_path: str) -> str:
        """Read file from the cloned repo. Token-budgeted."""
        full_path = REPOS_BASE / str(scan_id) / repo_type / file_path
        try:
            if full_path.exists():
                content = full_path.read_text(encoding="utf-8", errors="replace")
                return TokenBudget.truncate_to_budget(
                    content,
                    TokenBudget.MAX_TOKENS_FILE_SUMMARY,
                    label=str(file_path),
                )
            logger.warning(f"File not found: {full_path}")
            return ""
        except Exception as e:
            logger.error(f"Error reading {full_path}: {e}")
            return ""

    # ──────────────────────────────────────────────────────────────
    # Git Commit Message Enrichment
    # ──────────────────────────────────────────────────────────────

    def _get_commit_messages(
        self, scan_id: int, repo_type: str, commit_hashes: list
    ) -> list:
        """Pull full commit messages for the given hashes from the cloned repo."""
        if not commit_hashes:
            return []

        repo_path = REPOS_BASE / str(scan_id) / repo_type
        if not repo_path.exists():
            return commit_hashes

        messages = []
        for commit_hash in commit_hashes[:5]:  # Cap at 5 commits
            try:
                result = subprocess.run(
                    ["git", "log", "-1", "--pretty=format:%H%n%an%n%ai%n%s%n%b", str(commit_hash)],
                    cwd=str(repo_path),
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if result.returncode == 0 and result.stdout.strip():
                    msg = TokenBudget.truncate_to_budget(
                        result.stdout.strip(),
                        TokenBudget.MAX_TOKENS_COMMIT_MSG // 5,
                        label=f"commit_{commit_hash[:8]}",
                    )
                    messages.append(msg)
                else:
                    messages.append(f"[Commit: {commit_hash}]")
            except Exception as e:
                logger.warning(f"Could not fetch commit {commit_hash}: {e}")
                messages.append(f"[Commit: {commit_hash}]")

        return messages

    # ──────────────────────────────────────────────────────────────
    # AST-Level Change Summary (used in fallback path)
    # ──────────────────────────────────────────────────────────────

    def _build_ast_summary(
        self, upstream_content: str, fork_content: str, file_path: str
    ) -> dict:
        """Compute a structural diff of added/removed/modified top-level symbols."""
        ext = Path(file_path).suffix.lower()

        if ext == ".py":
            upstream_symbols = self._extract_python_symbols(upstream_content)
            fork_symbols = self._extract_python_symbols(fork_content)
        else:
            upstream_symbols = self._extract_symbols_regex(upstream_content, ext)
            fork_symbols = self._extract_symbols_regex(fork_content, ext)

        upstream_names = set(upstream_symbols.keys())
        fork_names = set(fork_symbols.keys())

        added = sorted(upstream_names - fork_names)
        removed = sorted(fork_names - upstream_names)
        common = upstream_names & fork_names
        modified = sorted(
            name for name in common
            if upstream_symbols[name] != fork_symbols[name]
        )

        return {
            "language": ext.lstrip(".") or "unknown",
            "upstream_symbol_count": len(upstream_names),
            "fork_symbol_count": len(fork_names),
            "added_in_upstream": added,
            "removed_in_upstream": removed,
            "modified": modified,
            "summary": self._summarize_ast(added, removed, modified),
        }

    def _extract_python_symbols(self, content: str) -> dict:
        """Extract top-level function/class definitions using Python AST."""
        if not content or content.startswith("(file not found"):
            return {}
        try:
            tree = ast.parse(content)
            symbols = {}
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    if any(
                        isinstance(p, ast.Module)
                        for p in ast.walk(tree)
                        if hasattr(p, "body") and node in getattr(p, "body", [])
                    ):
                        args = []
                        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            args = [a.arg for a in node.args.args]
                        symbols[node.name] = {
                            "type": type(node).__name__,
                            "lineno": node.lineno,
                            "args": args,
                        }
            return symbols
        except SyntaxError:
            return self._extract_symbols_regex(content, ".py")
        except Exception as e:
            logger.warning(f"AST parse error: {e}")
            return {}

    def _extract_symbols_regex(self, content: str, ext: str) -> dict:
        """Regex-based symbol extraction for non-Python files."""
        if not content or content.startswith("(file not found"):
            return {}

        patterns = {
            ".js": r"(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\(",
            ".ts": r"(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\(",
            ".tsx": r"(?:export\s+)?(?:const|function)\s+(\w+)",
            ".c": r"^\w[\w\s\*]+\s+(\w+)\s*\([^;]*\)\s*\{",
            ".cpp": r"^\w[\w\s\*:]+\s+(\w+)\s*\([^;]*\)\s*\{",
            ".java": r"(?:public|private|protected|static|\s)+[\w<>\[\]]+\s+(\w+)\s*\(",
            ".go": r"^func\s+(?:\([^)]+\)\s+)?(\w+)\s*\(",
            ".rb": r"^\s*def\s+(\w+)",
            ".rs": r"^(?:pub\s+)?fn\s+(\w+)\s*[<(]",
        }

        pattern = patterns.get(ext, r"(?:function|class|def)\s+(\w+)")
        matches = re.findall(pattern, content, re.MULTILINE)
        return {name: {"type": "symbol", "lineno": 0} for name in matches}

    def _summarize_ast(self, added: list, removed: list, modified: list) -> str:
        parts = []
        if added:
            parts.append(f"Upstream added {len(added)} symbol(s): {', '.join(added[:10])}")
        if removed:
            parts.append(
                f"Upstream removed {len(removed)} symbol(s) that fork still has: "
                f"{', '.join(removed[:10])}"
            )
        if modified:
            parts.append(f"{len(modified)} symbol(s) were modified: {', '.join(modified[:10])}")
        if not parts:
            parts.append("No top-level symbol changes detected (may be a config/template file).")
        return ". ".join(parts)

    @staticmethod
    def _infer_security_impact(file_path: str) -> str:
        """Simple heuristic to flag security-sensitive files."""
        if any(kw in (file_path or "").lower() for kw in ["auth", "jwt", "crypto", "security"]):
            return "HIGH"
        return "LOW"
