"""Normalize staff questions so typos like denssure still retrieve DentAssure docs."""

from __future__ import annotations

import re

_ALIASES = {
    r"\bdenssure\b": "dentassure",
    r"\bdensure\b": "dentassure",
    r"\bdent\s+assure\b": "dentassure",
    r"\bhow to take\b": "how to enroll buy subscribe",
    r"\bbest plan\b": "best plan care plus corporate complete care standard secure superior shield",
}


def expand_query(question: str) -> str:
    """Return a retrieval query with brand aliases expanded."""
    text = (question or "").strip()
    lowered = text.lower()
    extras: list[str] = []
    for pattern, replacement in _ALIASES.items():
        if re.search(pattern, lowered, flags=re.IGNORECASE):
            extras.append(replacement)
    if extras:
        return f"{text} {' '.join(extras)}"
    return text
