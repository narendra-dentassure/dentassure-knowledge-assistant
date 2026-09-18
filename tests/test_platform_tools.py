"""Platform tool tests — offline fixtures, no network required."""

from src.application.platform_tools import (
    PATIENT_COMPARE_EXAMPLES,
    classify_intent,
    extract_plan_slug,
    extract_treatment_queries,
    try_platform_tools,
)


def test_intent_splits_docs_clinic_and_compare() -> None:
    assert classify_intent("What is the grace period?") == "docs"
    assert classify_intent("What is scaling?") == "docs"
    assert classify_intent("how to take denssure plan which is best plan") == "docs"
    assert classify_intent("What plans do you have?") == "catalog"
    assert classify_intent("STANDARD STEER - Explain about this plan") == "plan_detail"
    assert classify_intent("Explain STANDARD SECURE waiting periods and coverage") == "docs"
    assert classify_intent("Explain COMPLETE CARE") == "docs"
    assert classify_intent("Clinic hours in Hyderabad") == "clinic"
    assert classify_intent("Root canal and scaling which plan is best") == "compare"


def test_extract_rct_and_scaling() -> None:
    found = extract_treatment_queries("root canal or scaling or implant which is best plan")
    assert "root canal" in found
    assert "scaling" in found
    assert "implant" in found


def test_informal_and_hinglish_compare_phrases() -> None:
    for question in PATIENT_COMPARE_EXAMPLES:
        assert classify_intent(question) == "compare", question

    assert "scaling" in extract_treatment_queries("scalling and consultaton which take")
    assert "OP Consultation" in extract_treatment_queries("scalling and consultaton which take")
    assert "scaling" in extract_treatment_queries("dant safai and doctor visit suggest")
    assert "OP Consultation" in extract_treatment_queries("opd checkup")
    assert classify_intent("i want checkup and teeth cleaning") == "compare"
    assert classify_intent("rct scaling") == "compare"


def test_offline_compare_op_consultation_and_scaling(monkeypatch) -> None:
    monkeypatch.setenv("PLATFORM_MODE", "offline")
    question = "If I want to go, OP consultation, scaling which plan should I buy ?"
    assert classify_intent(question) == "compare"
    result = try_platform_tools(question)
    assert result is not None
    assert "STANDARD STEER" in result.answer
    assert "Buy this:" in result.answer
    assert "DentAssure Customer Care" in result.answer


def test_offline_compare_returns_standard_steer(monkeypatch) -> None:
    monkeypatch.setenv("PLATFORM_MODE", "offline")
    result = try_platform_tools("Root canal and scaling which is the best plan?")
    assert result is not None
    assert result.mode == "offline"
    assert "STANDARD STEER" in result.answer
    assert "Root canal" in result.answer or "D0406" in result.answer


def test_offline_featured_plans_catalog(monkeypatch) -> None:
    monkeypatch.setenv("PLATFORM_MODE", "offline")
    result = try_platform_tools("What plans do you have?")
    assert result is not None
    assert result.intent == "catalog"
    assert "STANDARD STEER" in result.answer or "Smart Saver" in result.answer


def test_offline_standard_steer_plan_details(monkeypatch) -> None:
    monkeypatch.setenv("PLATFORM_MODE", "offline")
    question = "STANDARD STEER - Explain about this plan"
    assert extract_plan_slug(question) == "standard-steer"
    result = try_platform_tools(question)
    assert result is not None
    assert result.intent == "plan_detail"
    assert result.mode == "offline"
    assert "STANDARD STEER" in result.answer
    assert "1,999" in result.answer
    assert "dentassureplans.co.in/plan/standard-steer/details" in result.answer
    assert "DentAssure Customer Care" in result.answer


def test_offline_this_plan_follow_up_uses_history(monkeypatch) -> None:
    monkeypatch.setenv("PLATFORM_MODE", "offline")
    history = "DentAssure featured plans: STANDARD STEER PLAN0052 Rs 1999"
    assert classify_intent("Explain about this plan", history=history) == "plan_detail"
    result = try_platform_tools("Explain about this plan", history=history)
    assert result is not None
    assert "STANDARD STEER" in result.answer


def test_named_plans_split_api_rag_and_ungrounded(monkeypatch) -> None:
    monkeypatch.setenv("PLATFORM_MODE", "offline")
    assert extract_plan_slug("SUPERIOR SPARKLE explain this plan") == "superior-sparkle"
    assert classify_intent("SUPERIOR SPARKLE explain this plan") == "docs"
    assert try_platform_tools("SUPERIOR SPARKLE explain this plan") is None
    assert try_platform_tools("Explain STANDARD SECURE waiting periods and coverage") is None
    assert classify_intent("GOLD PREMIUM explain this plan") == "docs"
    assert try_platform_tools("STANDARD STEER - Explain about this plan") is not None
