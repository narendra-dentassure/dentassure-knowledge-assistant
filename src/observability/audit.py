"""JSONL audit log for every user question."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.config import PROJECT_ROOT
from src.logging_setup import configure_logging

logger = configure_logging()
AUDIT_PATH = PROJECT_ROOT / "logs" / "audit.jsonl"


def write_audit(event: dict[str, Any]) -> None:
    """Append one query event. Never store API keys."""
    payload = {
        "ts": datetime.now(timezone.utc).isoformat(),
        **event,
    }
    try:
        AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
        with AUDIT_PATH.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=True) + "\n")
    except Exception:
        logger.exception("Failed to write audit event")


def read_audit(limit: int = 50) -> list[dict[str, Any]]:
    """Return the latest audit events, newest first."""
    if not AUDIT_PATH.exists():
        return []
    lines = AUDIT_PATH.read_text(encoding="utf-8").splitlines()
    rows: list[dict[str, Any]] = []
    for line in lines[-limit:]:
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    rows.reverse()
    return rows
