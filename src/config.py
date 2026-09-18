"""Load runtime configuration from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name, str(default)).strip()
    try:
        return int(raw)
    except ValueError:
        return default


def _float_env(name: str, default: float) -> float:
    raw = os.getenv(name, str(default)).strip()
    try:
        return float(raw)
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    """Application settings used by ingest, retrieval, and the UI."""

    llm_provider: str
    openai_api_key: str
    openai_model: str
    gemini_api_key: str
    gemini_model: str
    chunk_size: int
    chunk_overlap: int
    retrieve_k: int
    rerank_k: int
    min_relevance_score: float
    data_dir: Path
    chroma_dir: Path
    log_level: str
    embedding_model_name: str
    rerank_model_name: str


def get_settings() -> Settings:
    """Return settings from the environment with safe defaults."""
    data_dir = Path(os.getenv("DATA_DIR", "data/sample_docs"))
    chroma_dir = Path(os.getenv("CHROMA_DIR", "storage/chroma"))
    if not data_dir.is_absolute():
        data_dir = PROJECT_ROOT / data_dir
    if not chroma_dir.is_absolute():
        chroma_dir = PROJECT_ROOT / chroma_dir

    return Settings(
        llm_provider=os.getenv("LLM_PROVIDER", "gemini").strip().lower(),
        openai_api_key=os.getenv("OPENAI_API_KEY", "").strip(),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip(),
        gemini_api_key=os.getenv("GEMINI_API_KEY", "").strip(),
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-3.6-flash").strip(),
        chunk_size=_int_env("CHUNK_SIZE", 900),
        chunk_overlap=_int_env("CHUNK_OVERLAP", 150),
        retrieve_k=_int_env("RETRIEVE_K", 8),
        rerank_k=_int_env("RERANK_K", 4),
        min_relevance_score=_float_env("MIN_RELEVANCE_SCORE", 0.18),
        data_dir=data_dir,
        chroma_dir=chroma_dir,
        log_level=os.getenv("LOG_LEVEL", "INFO").strip().upper(),
        embedding_model_name=os.getenv(
            "EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
        ).strip(),
        rerank_model_name=os.getenv(
            "RERANK_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2"
        ).strip(),
    )


def has_llm_credentials(settings: Settings | None = None) -> bool:
    """Return True when the selected provider has an API key configured."""
    settings = settings or get_settings()
    if settings.llm_provider == "openai":
        return bool(settings.openai_api_key) and "your_" not in settings.openai_api_key
    if settings.llm_provider == "gemini":
        return bool(settings.gemini_api_key) and "your_" not in settings.gemini_api_key
    return False
