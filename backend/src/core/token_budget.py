"""
token_budget.py

Enforces strict token limits for all context passed to LLM agents.
Uses a fast approximation (4 chars ≈ 1 token) to avoid adding a heavy
tokenizer dependency. All limits are tuned for Groq/LLaMA-3 70B with
a typical 8k context window.
"""


class TokenBudget:
    # ── Per-context block limits ────────────────────────────────────
    MAX_TOKENS_CONTEXT = 3500   # Total token budget for the context given to each agent
    MAX_TOKENS_FILE_SUMMARY = 300    # Per-file summary cap
    MAX_TOKENS_SYMBOL_SUMMARY = 150  # Per-symbol summary cap
    MAX_TOKENS_DIFF = 600            # Diff preview cap
    MAX_TOKENS_COMMIT_MSG = 200      # Commit messages block cap

    # ── Per-list length limits ──────────────────────────────────────
    MAX_CALLERS = 10          # Max caller/callee entries in retrieval bundle
    MAX_RELATED_FILES = 4     # Max related file summaries included in context
    MAX_CRITICAL_PATHS = 5    # Max critical path chains
    MAX_AFFECTED_FUNCTIONS = 20  # Max affected function names listed

    # ── Chars-per-token approximation ──────────────────────────────
    _CHARS_PER_TOKEN = 4

    @classmethod
    def estimate_tokens(cls, text: str) -> int:
        """Fast approximation: ~4 chars per token (no external tokenizer needed)."""
        if not text:
            return 0
        return max(1, len(text) // cls._CHARS_PER_TOKEN)

    @classmethod
    def truncate_to_budget(cls, text: str, max_tokens: int, label: str = "") -> str:
        """
        Truncate text to fit within the token budget.
        Appends a clear marker so agents know the content was trimmed.
        """
        if not text:
            return text
        max_chars = max_tokens * cls._CHARS_PER_TOKEN
        if len(text) <= max_chars:
            return text
        suffix = f"\n... [truncated — budget: {max_tokens} tokens{' for ' + label if label else ''}]"
        return text[: max_chars - len(suffix)] + suffix

    @classmethod
    def rank_and_trim(cls, items: list, max_items: int) -> list:
        """Return top-N items (caller is responsible for pre-sorting by relevance)."""
        return items[:max_items]

    @classmethod
    def fits_in_budget(cls, text: str, max_tokens: int) -> bool:
        """Check whether text fits without truncation."""
        return cls.estimate_tokens(text) <= max_tokens

    @classmethod
    def budget_report(cls, sections: dict[str, str]) -> dict[str, int]:
        """
        Return a {section_name: token_estimate} dict for logging/observability.
        Pass sections as {label: text}.
        """
        return {
            label: cls.estimate_tokens(text)
            for label, text in sections.items()
        }
