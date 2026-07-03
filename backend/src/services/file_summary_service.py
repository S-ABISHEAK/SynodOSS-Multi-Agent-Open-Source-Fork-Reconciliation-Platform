"""
file_summary_service.py

Generates compact semantic summaries for every file in a repository snapshot
during scan time. Summaries are stored in the file_summaries table and later
retrieved by RetrievalOrchestratorService at debate time.

Design:
- LLM-free first pass (AST + regex) for all files — no API cost, no rate limits.
- Structured summary text that agents can parse and reason over.
- Idempotent: existing summaries for (scan_id, file_path) are upserted, not duplicated.
"""

import ast
import os
import re
import logging
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from src.models.schema import FileSummary
from src.core.token_budget import TokenBudget

logger = logging.getLogger(__name__)

# Extensions we attempt to summarise
SUPPORTED_EXTENSIONS = {".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".java", ".rb", ".rs"}

# Skip these directories when walking repos
SKIP_DIRS = {".venv", "venv", "__pycache__", ".git", "node_modules", "dist", "build", ".next"}


class FileSummaryService:
    """
    Generates and persists per-file semantic summaries for a repository snapshot.
    Called once per scan in the Celery worker, after the graph is built.
    """

    def __init__(self, db: Session):
        self.db = db

    # ──────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────

    def generate_summaries(
        self,
        scan_id: int,
        repository_id: int,
        repo_path: str,
        max_files: int = 500,
    ) -> int:
        """
        Walk repo_path, generate a compact summary for each file, and persist to DB.

        Args:
            scan_id: The current scan's DB id (for snapshot versioning).
            repository_id: The repository's DB id.
            repo_path: Absolute path to the cloned repo on disk.
            max_files: Safety cap — do not process more than this many files.

        Returns:
            Number of file summaries written.
        """
        written = 0
        repo_root = Path(repo_path)

        for root, dirs, files in os.walk(repo_path):
            # Prune unwanted directories in-place
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]

            for filename in files:
                if written >= max_files:
                    logger.warning(
                        f"[file_summary] scan={scan_id} reached max_files={max_files}, stopping early"
                    )
                    return written

                full_path = Path(root) / filename
                ext = full_path.suffix.lower()
                if ext not in SUPPORTED_EXTENSIONS:
                    continue

                relative_path = str(full_path.relative_to(repo_root)).replace("\\", "/")

                try:
                    summary_data = self._summarise_file(full_path, relative_path, ext)
                    self._upsert_summary(scan_id, repository_id, relative_path, summary_data)
                    written += 1
                except Exception as e:
                    logger.warning(f"[file_summary] scan={scan_id} skipped {relative_path}: {e}")

        try:
            self.db.commit()
        except Exception as e:
            logger.error(f"[file_summary] scan={scan_id} commit failed: {e}")
            self.db.rollback()

        logger.info(f"[file_summary] scan={scan_id} repo={repository_id} | wrote {written} summaries")
        return written

    def get_summary(self, scan_id: int, file_path: str) -> Optional[FileSummary]:
        """Retrieve the summary for a specific file in a scan snapshot."""
        return (
            self.db.query(FileSummary)
            .filter_by(scan_id=scan_id, file_path=file_path, is_stale=False)
            .first()
        )

    def get_summaries_for_files(
        self, scan_id: int, file_paths: list[str]
    ) -> dict[str, FileSummary]:
        """Batch fetch summaries for a list of file paths. Returns {file_path: FileSummary}."""
        if not file_paths:
            return {}
        rows = (
            self.db.query(FileSummary)
            .filter(
                FileSummary.scan_id == scan_id,
                FileSummary.file_path.in_(file_paths),
                FileSummary.is_stale == False,  # noqa: E712
            )
            .all()
        )
        return {r.file_path: r for r in rows}

    def mark_stale(self, scan_id: int, file_path: Optional[str] = None) -> int:
        """
        Mark summaries as stale.
        If file_path is given, marks only that file. Otherwise marks all files in the scan.
        Returns count of rows marked stale.
        """
        query = self.db.query(FileSummary).filter_by(scan_id=scan_id)
        if file_path:
            query = query.filter_by(file_path=file_path)
        count = query.update({"is_stale": True}, synchronize_session=False)
        self.db.commit()
        return count

    # ──────────────────────────────────────────────────────────────
    # Summary Generation (LLM-free)
    # ──────────────────────────────────────────────────────────────

    def _summarise_file(self, full_path: Path, relative_path: str, ext: str) -> dict:
        """
        Generate a structured summary dict for a single file.
        Uses Python AST for .py files, regex for everything else.
        Never calls an LLM — 100% deterministic and fast.
        """
        try:
            content = full_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            content = ""

        lines = content.splitlines()
        line_count = len(lines)

        if ext == ".py":
            symbols, imports = self._analyse_python(content)
        else:
            symbols, imports = self._analyse_generic(content, ext)

        language = ext.lstrip(".")

        # Build the compact summary text that agents will read
        summary_parts = [f"File: {relative_path}"]
        if symbols:
            summary_parts.append(f"Exports: {', '.join(symbols[:20])}")
        if imports:
            summary_parts.append(f"Imports: {', '.join(imports[:15])}")
        summary_parts.append(f"Lines: {line_count} | Symbols: {len(symbols)} | Language: {language}")

        summary_text = " | ".join(summary_parts)

        # Apply token budget to the summary text itself
        summary_text = TokenBudget.truncate_to_budget(
            summary_text, TokenBudget.MAX_TOKENS_FILE_SUMMARY, label=relative_path
        )

        return {
            "language": language,
            "summary_text": summary_text,
            "symbol_count": len(symbols),
            "import_count": len(imports),
            "line_count": line_count,
            "exported_symbols": symbols[:50],   # cap stored list
            "imported_modules": imports[:30],
        }

    def _analyse_python(self, content: str) -> tuple[list[str], list[str]]:
        """Extract top-level symbols and imports from Python source using AST."""
        symbols: list[str] = []
        imports: list[str] = []

        if not content.strip():
            return symbols, imports

        try:
            tree = ast.parse(content)
        except SyntaxError:
            return self._analyse_generic(content, ".py")

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                symbols.append(node.name)
            elif isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                # Only top-level functions (parent is Module)
                symbols.append(node.name)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module.split(".")[0])

        # Deduplicate while preserving order
        seen: set[str] = set()
        symbols = [s for s in symbols if not (s in seen or seen.add(s))]
        seen.clear()
        imports = [i for i in imports if not (i in seen or seen.add(i))]

        return symbols, imports

    def _analyse_generic(self, content: str, ext: str) -> tuple[list[str], list[str]]:
        """Regex-based symbol + import extraction for non-Python files."""
        symbol_patterns: dict[str, str] = {
            ".ts": r"(?:export\s+)?(?:async\s+)?(?:function|class|const|interface|type)\s+(\w+)",
            ".tsx": r"(?:export\s+)?(?:async\s+)?(?:function|class|const|interface|type)\s+(\w+)",
            ".js": r"(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\(",
            ".jsx": r"(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\(",
            ".go": r"^func\s+(?:\([^)]+\)\s+)?(\w+)\s*\(",
            ".java": r"(?:public|private|protected|static|\s)+[\w<>\[\]]+\s+(\w+)\s*\(",
            ".rb": r"^\s*def\s+(\w+)",
            ".rs": r"^(?:pub\s+)?fn\s+(\w+)\s*[<(]",
        }
        import_patterns: dict[str, str] = {
            ".ts": r"(?:import|require)\s+.*?['\"](.+?)['\"]",
            ".tsx": r"(?:import|require)\s+.*?['\"](.+?)['\"]",
            ".js": r"(?:import|require)\s+.*?['\"](.+?)['\"]",
            ".jsx": r"(?:import|require)\s+.*?['\"](.+?)['\"]",
            ".go": r'import\s+"([^"]+)"',
            ".java": r"^import\s+([\w.]+);",
            ".rb": r"require\s+['\"](.+?)['\"]",
            ".rs": r"use\s+([\w:]+)",
        }

        sym_pat = symbol_patterns.get(ext, r"(?:function|class|def)\s+(\w+)")
        imp_pat = import_patterns.get(ext, r"import\s+['\"](.+?)['\"]")

        symbols = list(dict.fromkeys(re.findall(sym_pat, content, re.MULTILINE)))
        imports_raw = re.findall(imp_pat, content, re.MULTILINE)
        imports = list(dict.fromkeys(
            m.split("/")[0].split(".")[0] for m in imports_raw if m
        ))

        return symbols, imports

    # ──────────────────────────────────────────────────────────────
    # Persistence
    # ──────────────────────────────────────────────────────────────

    def _upsert_summary(
        self,
        scan_id: int,
        repository_id: int,
        file_path: str,
        data: dict,
    ) -> FileSummary:
        """Insert or update a FileSummary row for (scan_id, file_path)."""
        existing = (
            self.db.query(FileSummary)
            .filter_by(scan_id=scan_id, file_path=file_path)
            .first()
        )
        if existing:
            existing.language = data["language"]
            existing.summary_text = data["summary_text"]
            existing.symbol_count = data["symbol_count"]
            existing.import_count = data["import_count"]
            existing.line_count = data["line_count"]
            existing.exported_symbols = data["exported_symbols"]
            existing.imported_modules = data["imported_modules"]
            existing.is_stale = False
            return existing

        row = FileSummary(
            scan_id=scan_id,
            repository_id=repository_id,
            file_path=file_path,
            language=data["language"],
            summary_text=data["summary_text"],
            symbol_count=data["symbol_count"],
            import_count=data["import_count"],
            line_count=data["line_count"],
            exported_symbols=data["exported_symbols"],
            imported_modules=data["imported_modules"],
            is_stale=False,
        )
        self.db.add(row)
        return row
