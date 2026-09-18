"""Use-case catalog tests."""

from src.application.use_cases import get_use_case, get_use_cases, match_use_case


def test_catalog_has_named_use_cases() -> None:
    cases = get_use_cases()
    ids = [item.use_case_id for item in cases]
    assert "UC-01" in ids
    assert "UC-10" in ids
    assert "UC-11" in ids
    assert get_use_case("UC-10").must_refuse is True
    assert "plan_selection_guide" in get_use_case("UC-04").expected_source
    assert get_use_case("UC-11").expected_source.startswith("featured")
    assert "STEER" in (get_use_case("UC-11").follow_up or "")
    assert match_use_case("STANDARD STEER - Explain about this plan").use_case_id == "UC-11"
    assert match_use_case("Explain STANDARD SECURE waiting periods and coverage").use_case_id == "UC-04"


def test_match_renewal_and_refusal_questions() -> None:
    renewal = match_use_case("What are the key guidelines for DentAssure policy renewal?")
    assert renewal is not None
    assert renewal.use_case_id == "UC-01"
    refusal = match_use_case("What is the CEO's personal mobile number and home address?")
    assert refusal is not None
    assert refusal.must_refuse is True
