"""
policy_context_builder.py

Assembles retrieved policy chunks into a bounded PolicyContextBundle
suitable for injection into the multi-agent debate context.

Enforces:
- Max 5 chunks
- Max 1200 tokens total
- Deduplication by chunk_hash
- Structured text output for agent prompts
"""
import logging
from dataclasses import dataclass, field

from src.services.policy.policy_retriever import RetrievedPolicyChunk

logger = logging.getLogger(__name__)

MAX_POLICY_TOKENS = 1200
CHARS_PER_TOKEN = 4  # rough approximation


@dataclass
class PolicyContextBundle:
    chunks: list[RetrievedPolicyChunk] = field(default_factory=list)
    total_token_estimate: int = 0
    policy_names: list[str] = field(default_factory=list)  # for quick display
    formatted_context: str = ""  # ready-to-inject string for agent prompts
    is_empty: bool = True


def build_policy_context(retrieved_chunks: list[RetrievedPolicyChunk]) -> PolicyContextBundle:
    """
    Assemble a bounded PolicyContextBundle from retrieved policy chunks.

    Args:
        retrieved_chunks: Output from PolicyRetriever.retrieve().

    Returns:
        PolicyContextBundle ready for injection into the debate context dict.
    """
    if not retrieved_chunks:
        return PolicyContextBundle(is_empty=True)

    selected: list[RetrievedPolicyChunk] = []
    total_chars = 0
    max_chars = MAX_POLICY_TOKENS * CHARS_PER_TOKEN

    for chunk in retrieved_chunks:
        chunk_chars = len(chunk.chunk_text)
        if total_chars + chunk_chars > max_chars:
            logger.info(f"[policy_context_builder] Token budget reached — stopping at {len(selected)} chunks")
            break
        selected.append(chunk)
        total_chars += chunk_chars

    if not selected:
        return PolicyContextBundle(is_empty=True)

    # Build the formatted context string for agent injection
    lines = ["=== ENTERPRISE POLICY CONTEXT ==="]
    lines.append(
        "The following enterprise policies are relevant to this conflict. "
        "Reference them in your analysis by policy name if they directly affect your argument."
    )
    lines.append("")

    for i, chunk in enumerate(selected, 1):
        lines.append(f"[Policy {i}] {chunk.policy_name} ({chunk.policy_category}) — Priority: {chunk.policy_priority}")
        lines.append(f"Relevance: {chunk.reason} (similarity={chunk.similarity_score})")
        lines.append(f"Policy Text: {chunk.chunk_text}")
        lines.append("")

    lines.append("=== END POLICY CONTEXT ===")
    formatted = "\n".join(lines)

    token_estimate = max(1, total_chars // CHARS_PER_TOKEN)
    policy_names = list(dict.fromkeys(c.policy_name for c in selected))  # deduplicated order

    logger.info(
        f"[policy_context_builder] Built policy context: "
        f"{len(selected)} chunks, ~{token_estimate} tokens, policies={policy_names}"
    )

    return PolicyContextBundle(
        chunks=selected,
        total_token_estimate=token_estimate,
        policy_names=policy_names,
        formatted_context=formatted,
        is_empty=False,
    )
