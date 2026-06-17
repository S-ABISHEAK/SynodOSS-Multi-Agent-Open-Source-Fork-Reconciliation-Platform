import os
import ast
import re
import subprocess
import logging
from pathlib import Path
from src.models.schema import ReconciliationUnit

logger = logging.getLogger(__name__)

# Max characters to inject per file (keeps within ~6k tokens)
MAX_FILE_CHARS = 8000
# Base path where repos are cloned
REPOS_BASE = Path(__file__).parent.parent.parent / "data" / "repos"


class ConflictContextBuilder:
    def build_context(self, unit: ReconciliationUnit) -> dict:
        """
        Builds a rich, grounded context dict for the agents.
        Includes: full file contents, git commit messages, AST-level change summary,
        and graph-aware impact analysis (Stage 2 additions from graph_02.md).
        """
        scan_id = unit.scan_id
        file_path = unit.file_path  # e.g. "apps/backend/routes/ingest.py"

        upstream_content = self._read_file(scan_id, "upstream", file_path)
        fork_content = self._read_file(scan_id, "fork", file_path)

        upstream_commit_messages = self._get_commit_messages(
            scan_id, "upstream", unit.upstream_commits or []
        )
        fork_commit_messages = self._get_commit_messages(
            scan_id, "fork", unit.fork_commits or []
        )

        ast_summary = self._build_ast_summary(upstream_content, fork_content, file_path)

        # Provide the full diff (not truncated to 1000 chars like before)
        diff_preview = unit.diff_hunk or "(no diff available)"

        context = {
            "file_path": file_path,
            "complexity_score": unit.complexity_score,
            "diff_preview": diff_preview,
            "upstream_file_content": upstream_content or "(file not found in upstream)",
            "fork_file_content": fork_content or "(file not found in fork — may have been deleted)",
            "upstream_commit_messages": upstream_commit_messages,
            "fork_commit_messages": fork_commit_messages,
            "ast_summary": ast_summary,
            # ── Graph-Aware Impact Context (graph_02.md Stage 2) ──────────
            "changed_symbol": unit.symbol or "Unknown",
            "impact_score": unit.impact_score or 0.0,
            "affected_functions": unit.affected_functions or [],
            "affected_modules": unit.affected_modules or [],
            "critical_paths": unit.critical_paths or [],
            "dependency_depth": unit.dependency_depth or 0,
            "architectural_layer": unit.architectural_layer or "Unknown",
        }
        return context


    # ──────────────────────────────────────────────────────────
    # File Reading
    # ──────────────────────────────────────────────────────────
    def _read_file(self, scan_id: int, repo_type: str, file_path: str) -> str:
        """Read the actual file from the cloned repo on disk."""
        full_path = REPOS_BASE / str(scan_id) / repo_type / file_path
        try:
            if full_path.exists():
                content = full_path.read_text(encoding="utf-8", errors="replace")
                if len(content) > MAX_FILE_CHARS:
                    content = content[:MAX_FILE_CHARS] + f"\n\n... [truncated at {MAX_FILE_CHARS} chars] ..."
                return content
            else:
                logger.warning(f"File not found: {full_path}")
                return ""
        except Exception as e:
            logger.error(f"Error reading {full_path}: {e}")
            return ""

    # ──────────────────────────────────────────────────────────
    # Git Commit Message Enrichment
    # ──────────────────────────────────────────────────────────
    def _get_commit_messages(self, scan_id: int, repo_type: str, commit_hashes: list) -> list:
        """Pull full commit messages for the given hashes from the cloned repo."""
        if not commit_hashes:
            return []

        repo_path = REPOS_BASE / str(scan_id) / repo_type
        if not repo_path.exists():
            return commit_hashes  # Return the raw hashes as fallback

        messages = []
        for commit_hash in commit_hashes[:5]:  # Cap at 5 commits to avoid context bloat
            try:
                result = subprocess.run(
                    ["git", "log", "-1", "--pretty=format:%H%n%an%n%ai%n%s%n%b", str(commit_hash)],
                    cwd=str(repo_path),
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0 and result.stdout.strip():
                    messages.append(result.stdout.strip())
                else:
                    messages.append(f"[Commit: {commit_hash}]")
            except Exception as e:
                logger.warning(f"Could not fetch commit {commit_hash}: {e}")
                messages.append(f"[Commit: {commit_hash}]")

        return messages

    # ──────────────────────────────────────────────────────────
    # AST-Level Change Summary
    # ──────────────────────────────────────────────────────────
    def _build_ast_summary(self, upstream_content: str, fork_content: str, file_path: str) -> dict:
        """
        Compute a structural diff of added/removed/modified top-level symbols.
        Uses Python AST for .py files, regex fallback for others.
        """
        ext = Path(file_path).suffix.lower()

        if ext == ".py":
            upstream_symbols = self._extract_python_symbols(upstream_content)
            fork_symbols = self._extract_python_symbols(fork_content)
        else:
            upstream_symbols = self._extract_symbols_regex(upstream_content, ext)
            fork_symbols = self._extract_symbols_regex(fork_content, ext)

        upstream_names = set(upstream_symbols.keys())
        fork_names = set(fork_symbols.keys())

        added = sorted(upstream_names - fork_names)       # In upstream but not fork = upstream added them
        removed = sorted(fork_names - upstream_names)     # In fork but not upstream = fork had them, upstream removed
        common = upstream_names & fork_names
        modified = sorted(
            name for name in common
            if upstream_symbols[name] != fork_symbols[name]
        )

        return {
            "language": ext.lstrip(".") or "unknown",
            "upstream_symbol_count": len(upstream_names),
            "fork_symbol_count": len(fork_names),
            "added_in_upstream": added,      # Upstream added these (fork doesn't have them)
            "removed_in_upstream": removed,  # Fork has these, upstream deleted them
            "modified": modified,            # Both have it but different signatures/line counts
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
                    # Only top-level (parent is Module)
                    if any(isinstance(p, ast.Module) for p in ast.walk(tree) if hasattr(p, 'body') and node in getattr(p, 'body', [])):
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
            parts.append(f"Upstream removed {len(removed)} symbol(s) that fork still has: {', '.join(removed[:10])}")
        if modified:
            parts.append(f"{len(modified)} symbol(s) were modified: {', '.join(modified[:10])}")
        if not parts:
            parts.append("No top-level symbol changes detected (may be a config/template file).")
        return ". ".join(parts)
