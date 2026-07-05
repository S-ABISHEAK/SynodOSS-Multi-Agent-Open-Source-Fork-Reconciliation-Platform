"""
policy_chunker.py

Splits raw policy text into bounded chunks (≤300 tokens each).
Deduplicates chunks via SHA256 hash comparison.
No LLM calls — pure text splitting.
"""
import hashlib
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# Approximate tokens per word (English average)
_WORDS_PER_TOKEN = 0.75
# Target max tokens per chunk
MAX_TOKENS_PER_CHUNK = 300
# Estimated max words per chunk
MAX_WORDS_PER_CHUNK = int(MAX_TOKENS_PER_CHUNK / _WORDS_PER_TOKEN)
# Overlap between consecutive chunks (in words) for better retrieval continuity
CHUNK_OVERLAP_WORDS = 30


@dataclass
class PolicyTextChunk:
    chunk_index: int
    chunk_text: str
    chunk_hash: str
    token_count: int
    is_duplicate: bool = False


def chunk_policy_text(text: str) -> list[PolicyTextChunk]:
    """
    Split policy text into overlapping, bounded chunks.

    Strategy:
    - Split by paragraph (double newlines) first for semantic coherence.
    - If a paragraph exceeds MAX_WORDS_PER_CHUNK, split by sentence.
    - Apply a sliding window with CHUNK_OVERLAP_WORDS to maintain continuity.
    - Deduplicate via SHA256 hash.

    Returns a list of PolicyTextChunk objects (duplicates flagged, not removed).
    """
    # Step 1: Split by paragraphs
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

    # Step 2: Build word groups from paragraphs
    word_groups: list[list[str]] = []
    for para in paragraphs:
        words = para.split()
        if len(words) <= MAX_WORDS_PER_CHUNK:
            word_groups.append(words)
        else:
            # Split long paragraph into sentence-level chunks
            sentences = _split_into_sentences(para)
            buffer: list[str] = []
            for sentence in sentences:
                s_words = sentence.split()
                if len(buffer) + len(s_words) > MAX_WORDS_PER_CHUNK:
                    if buffer:
                        word_groups.append(buffer)
                    buffer = s_words
                else:
                    buffer.extend(s_words)
            if buffer:
                word_groups.append(buffer)

    # Step 3: Flatten into sliding window chunks with overlap
    chunks: list[PolicyTextChunk] = []
    seen_hashes: set[str] = set()
    flat_words: list[str] = []
    for group in word_groups:
        flat_words.extend(group)
        flat_words.append("")  # paragraph boundary marker

    i = 0
    chunk_index = 0
    while i < len(flat_words):
        window = flat_words[i: i + MAX_WORDS_PER_CHUNK]
        chunk_text = " ".join(w for w in window if w).strip()
        if not chunk_text:
            i += max(1, MAX_WORDS_PER_CHUNK - CHUNK_OVERLAP_WORDS)
            continue

        chunk_hash = _hash(chunk_text)
        is_duplicate = chunk_hash in seen_hashes
        if not is_duplicate:
            seen_hashes.add(chunk_hash)

        estimated_tokens = max(1, len(chunk_text.split()))

        chunks.append(PolicyTextChunk(
            chunk_index=chunk_index,
            chunk_text=chunk_text,
            chunk_hash=chunk_hash,
            token_count=estimated_tokens,
            is_duplicate=is_duplicate,
        ))
        chunk_index += 1
        i += max(1, MAX_WORDS_PER_CHUNK - CHUNK_OVERLAP_WORDS)

    logger.info(f"[policy_chunker] {len(chunks)} chunks created ({sum(1 for c in chunks if c.is_duplicate)} duplicates)")
    return chunks


def _split_into_sentences(text: str) -> list[str]:
    """Simple sentence splitter using punctuation markers."""
    import re
    sentences = re.split(r'(?<=[.!?])\s+', text)
    return [s.strip() for s in sentences if s.strip()]


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
