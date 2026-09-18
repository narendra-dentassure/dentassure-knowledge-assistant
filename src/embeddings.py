"""Local embedding model wrapper."""

from __future__ import annotations

from functools import lru_cache

from sentence_transformers import SentenceTransformer

from src.config import get_settings
from src.logging_setup import configure_logging

logger = configure_logging()


@lru_cache(maxsize=1)
def get_embedding_model() -> SentenceTransformer:
    """Load the sentence-transformer model once per process."""
    settings = get_settings()
    logger.info("Loading embedding model: %s", settings.embedding_model_name)
    return SentenceTransformer(settings.embedding_model_name)


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Return embeddings for a list of texts."""
    model = get_embedding_model()
    vectors = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    return [vector.tolist() for vector in vectors]
