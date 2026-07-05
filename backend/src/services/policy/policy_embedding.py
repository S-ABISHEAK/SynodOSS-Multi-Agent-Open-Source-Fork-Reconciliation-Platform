"""
policy_embedding.py

Generates sentence embeddings for policy chunks using sentence-transformers.
Uses all-MiniLM-L6-v2 model — runs entirely locally, no API cost.
Caches the model singleton to avoid reloading on every call.
"""
import logging
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

# Model singleton — loaded once per process
_MODEL = None
_MODEL_NAME = "all-MiniLM-L6-v2"


def _get_model():
    """Lazy-load the sentence-transformers model singleton."""
    global _MODEL
    if _MODEL is None:
        try:
            from sentence_transformers import SentenceTransformer
            logger.info(f"[policy_embedding] Loading embedding model: {_MODEL_NAME}")
            _MODEL = SentenceTransformer(_MODEL_NAME)
            logger.info("[policy_embedding] Model loaded successfully")
        except ImportError:
            logger.error("[policy_embedding] sentence-transformers not installed. Run: uv add sentence-transformers")
            raise
    return _MODEL


def embed_text(text: str) -> list[float]:
    """
    Generate a normalized embedding vector for a single text string.

    Returns:
        A list of floats (384 dims for all-MiniLM-L6-v2).
    """
    model = _get_model()
    embedding = model.encode(text, normalize_embeddings=True)
    return embedding.tolist()


def embed_texts(texts: list[str]) -> list[list[float]]:
    """
    Batch-embed multiple texts for efficiency.

    Returns:
        List of embedding vectors.
    """
    if not texts:
        return []
    model = _get_model()
    embeddings = model.encode(texts, normalize_embeddings=True, batch_size=32, show_progress_bar=False)
    return [e.tolist() for e in embeddings]


def cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """
    Compute cosine similarity between two embedding vectors.
    Both are assumed to be already normalized (from embed_text).
    For normalized vectors, cosine similarity = dot product.

    Returns:
        Float in range [-1, 1]. Values ≥ 0.25 are considered relevant.
    """
    a = np.array(vec_a, dtype=np.float32)
    b = np.array(vec_b, dtype=np.float32)
    return float(np.dot(a, b))
