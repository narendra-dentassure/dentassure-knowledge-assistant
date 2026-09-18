"""Role catalog tests."""

from src.application.roles import get_role, list_role_ids, role_instruction, role_label


def test_three_roles() -> None:
    ids = list_role_ids()
    assert ids == ["Visitor", "Front Desk", "Claims Desk"]


def test_unknown_role_falls_back_to_visitor() -> None:
    assert get_role("unknown").role_id == "Visitor"
    assert get_role("").role_id == "Visitor"
    assert "patient" in role_instruction("not-a-role").lower()


def test_role_changes_tone_not_facts() -> None:
    visitor = role_instruction("Visitor")
    claims = role_instruction("Claims Desk")
    assert visitor != claims
    assert "Customer Care" in visitor or "enroll" in visitor.lower()
    assert "co-pay" in claims.lower() or "waiting" in claims.lower()
    assert role_label("Front Desk").startswith("Network")
