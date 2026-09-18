"""Cross-encoder reranking of hybrid retrieval candidates."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from src.config import get_settings
from src.logging_setup import configure_logging

logger = configure_logging()


@lru_cache(maxsize=1)
def _load_cross_encoder():
    """Load the cross-encoder once. Return None if the model cannot load."""
    try:
        from sentence_transformers import CrossEncoder

        settings = get_settings()
        logger.info("Loading reranker: %s", settings.rerank_model_name)
        return CrossEncoder(settings.rerank_model_name)
    except Exception:
        logger.exception("Cross-encoder unavailable; falling back to RRF scores")
        return None


def rerank_hits(query: str, hits: list[dict[str, Any]], rerank_k: int) -> list[dict[str, Any]]:
    """Rerank hybrid hits and keep the top rerank_k results."""
    if not hits:
        return []

    model = _load_cross_encoder()
    if model is None:
        ranked = sorted(hits, key=lambda item: item.get("rrf_score", 0.0), reverse=True)
        for hit in ranked:
            hit["relevance_score"] = float(hit.get("rrf_score", 0.0))
        return ranked[:rerank_k]

    pairs = [(query, hit["text"]) for hit in hits]
    scores = model.predict(pairs)
    for hit, score in zip(hits, scores):
        hit["relevance_score"] = float(score)

    ranked = sorted(hits, key=lambda item: item["relevance_score"], reverse=True)
    logger.info("Reranked %s hits down to %s", len(hits), min(rerank_k, len(ranked)))
    return ranked[:rerank_k]
