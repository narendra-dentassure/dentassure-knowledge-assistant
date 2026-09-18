"""Audience roles: tone only. Facts always come from DentAssure documents or APIs."""

from __future__ import annotations

from dataclasses import dataclass

from src.domain.models import RoleName


@dataclass(frozen=True)
class AssistantRole:
    """One audience the assistant can speak to."""

    role_id: RoleName
    label: str
    audience: str
    instruction: str


ROLE_CATALOG: tuple[AssistantRole, ...] = (
    AssistantRole(
        role_id="Visitor",
        label="Visitor / patient",
        audience="Public website or clinic walk-in. May or may not already have a plan.",
        instruction=(
            "Write for a patient or website visitor in plain English. Explain how to enroll, "
            "which plan family fits, where to find a clinic, and when to call Customer Care. "
            "Do not give clinical treatment advice. Do not invent prices."
        ),
    ),
    AssistantRole(
        role_id="Front Desk",
        label="Network clinic front desk",
        audience="Reception at a DentAssure network clinic.",
        instruction=(
            "Write for reception. Tell the patient what to show, what is cashless, "
            "and when to raise a DentAssure pre-authorization before treatment starts."
        ),
    ),
    AssistantRole(
        role_id="Claims Desk",
        label="DentAssure claims desk",
        audience="Internal claims officer quoting policy.",
        instruction=(
            "Write for a DentAssure claims officer. Quote waiting periods, annual limits, "
            "pre-auth rules, and co-pay exactly as written in the documents."
        ),
    ),
)


def list_role_ids() -> list[RoleName]:
    """Role ids for the UI select box."""
    return [item.role_id for item in ROLE_CATALOG]


def get_role(role: str) -> AssistantRole:
    """Return the catalog entry, or Visitor if the id is unknown."""
    for item in ROLE_CATALOG:
        if item.role_id == role:
            return item
    return ROLE_CATALOG[0]


def role_label(role: str) -> str:
    """Human-readable label for the sidebar."""
    return get_role(role).label


def role_instruction(role: str) -> str:
    """Prompt fragment. Roles change tone, never DentAssure facts."""
    return get_role(role).instruction
