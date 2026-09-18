"""Input guardrails for enterprise-safe querying."""

from __future__ import annotations

import re

_INJECTION_PATTERNS = [
    r"ignore (all|any|previous|prior) (instructions|prompts)",
    r"system prompt",
    r"reveal (your|the) hidden",
    r"jailbreak",
    r"developer mode",
    r"exfiltrat",
    r"override (the )?rules",
]


def inspect_query(question: str) -> str | None:
    """Return a guardrail code, or None if the query may proceed."""
    text = (question or "").strip()
    if not text:
        return "empty_question"
    if len(text) > 2000:
        return "query_too_long"
    lowered = text.lower()
    for pattern in _INJECTION_PATTERNS:
        if re.search(pattern, lowered):
            return "prompt_injection"
    if re.search(r"\bceo\b", lowered) and any(
        token in lowered for token in ("mobile", "phone", "home address", "personal")
    ):
        return "pii_probe"
    return None


def guardrail_message(code: str) -> str:
    from src.application.disclaimer import with_customer_care_notice

    messages = {
        "empty_question": "Please enter a question.",
        "query_too_long": "Please shorten the question to under 2000 characters.",
        "prompt_injection": (
            "This assistant only answers from DentAssure Health Plans documents and public plan/clinic data. "
            "I cannot ignore those rules or reveal hidden instructions."
        ),
        "pii_probe": (
            "I cannot provide personal contact details or home addresses. "
            "For plan help call DentAssure Customer Care +91 888 668 6850."
        ),
    }
    return with_customer_care_notice(messages.get(code, "The question could not be processed."))
