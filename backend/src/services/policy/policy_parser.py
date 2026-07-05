"""
policy_parser.py

Parses uploaded policy documents into raw text strings.
Supports: Markdown (.md), TXT, PDF, DOCX, JSON, YAML.
No LLM calls — pure file parsing only.
"""
import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def parse_policy_file(file_path: str, filename: str) -> Optional[str]:
    """
    Parse a policy document file into a raw text string.

    Args:
        file_path: Absolute path to the temporary uploaded file on disk.
        filename: Original filename (used to determine file type).

    Returns:
        Extracted text string, or None if parsing fails.
    """
    ext = Path(filename).suffix.lower()
    try:
        if ext in {".md", ".txt"}:
            return _parse_text(file_path)
        elif ext == ".pdf":
            return _parse_pdf(file_path)
        elif ext == ".docx":
            return _parse_docx(file_path)
        elif ext == ".json":
            return _parse_json(file_path)
        elif ext in {".yml", ".yaml"}:
            return _parse_yaml(file_path)
        else:
            logger.warning(f"[policy_parser] Unsupported file type: {ext}")
            return None
    except Exception as e:
        logger.error(f"[policy_parser] Failed to parse {filename}: {e}")
        return None


def _parse_text(file_path: str) -> str:
    return Path(file_path).read_text(encoding="utf-8", errors="replace")


def _parse_pdf(file_path: str) -> str:
    from pypdf import PdfReader
    reader = PdfReader(file_path)
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(pages)


def _parse_docx(file_path: str) -> str:
    from docx import Document
    doc = Document(file_path)
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n".join(paragraphs)


def _parse_json(file_path: str) -> str:
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    # Flatten JSON to human-readable text
    return _flatten_json(data)


def _parse_yaml(file_path: str) -> str:
    import yaml
    with open(file_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return _flatten_json(data)


def _flatten_json(obj, prefix="") -> str:
    """Recursively flatten a dict/list into key: value lines."""
    lines = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            key = f"{prefix}.{k}" if prefix else k
            lines.append(_flatten_json(v, key))
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            lines.append(_flatten_json(item, f"{prefix}[{i}]"))
    else:
        lines.append(f"{prefix}: {obj}")
    return "\n".join(lines)
