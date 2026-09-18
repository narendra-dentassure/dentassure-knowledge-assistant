"""Central logging configuration for the knowledge assistant."""

from __future__ import annotations

import logging
from src.config import PROJECT_ROOT, get_settings


def configure_logging() -> logging.Logger:
    """Configure console + file logging and return the app logger."""
    settings = get_settings()
    log_dir = PROJECT_ROOT / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("dentassure_assistant")
    if logger.handlers:
        return logger

    logger.setLevel(getattr(logging, settings.log_level, logging.INFO))
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )

    file_handler = logging.FileHandler(log_dir / "app.log", encoding="utf-8")
    file_handler.setFormatter(formatter)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
    logger.propagate = False
    return logger
