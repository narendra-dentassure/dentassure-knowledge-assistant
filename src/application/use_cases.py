"""Named DentAssure scenarios for visitors, front desk, and claims."""

from __future__ import annotations

from src.domain.models import UseCase

USE_CASES: list[UseCase] = [
    UseCase(
        use_case_id="UC-01",
        name="Policy renewal advisory",
        persona="Claims Desk",
        brand="DentAssure",
        question="What are the key guidelines for DentAssure policy renewal?",
        follow_up="What happens if premium is not paid during the grace period?",
        expected_source="dentassure_policy_guide.pdf",
        expected_keywords=["grace", "renewal", "T-30"],
        why_it_matters="Members and front desk must quote the same renewal rules.",
    ),
    UseCase(
        use_case_id="UC-02",
        name="Pre-authorization gate",
        persona="Claims Desk",
        brand="DentAssure",
        question="When is pre-authorization mandatory for DentAssure claims?",
        follow_up="What is paid if treatment starts without pre-auth?",
        expected_source="dentassure_policy_guide.pdf",
        expected_keywords=["pre-authorization", "12000", "RCT"],
        why_it_matters="Stops ineligible cashless work before treatment starts.",
    ),
    UseCase(
        use_case_id="UC-03",
        name="Annual limit and co-pay",
        persona="Claims Desk",
        brand="DentAssure",
        question="What is the annual limit and co-pay for DentAssure Plus versus Care?",
        follow_up=None,
        expected_source="dentassure_policy_guide.pdf",
        expected_keywords=["40,000", "15,000", "co-pay"],
        why_it_matters="Prevents over-promising benefits at the counter or on chat.",
    ),
    UseCase(
        use_case_id="UC-04",
        name="How to take a plan",
        persona="Visitor",
        brand="DentAssure",
        question="How to take a DentAssure plan which is the best plan?",
        follow_up="Explain STANDARD SECURE waiting periods and coverage",
        expected_source="dentassure_plan_selection_guide.txt",
        expected_keywords=["Standard Secure", "Superior Shield", "enroll"],
        why_it_matters="Website visitors ask this first. Plan-choice advice stays in documents, not the live SKU API.",
    ),
    UseCase(
        use_case_id="UC-05",
        name="Cashless at the clinic",
        persona="Front Desk",
        brand="DentAssure",
        question="How does a patient use DentAssure cashless at a network clinic?",
        follow_up="What should reception check before the chair is booked?",
        expected_source="dentassure_clinic_front_desk_sop.docx",
        expected_keywords=["cashless", "member", "pre-auth"],
        why_it_matters="Front desk is who the patient meets. The SOP must match policy.",
    ),
    UseCase(
        use_case_id="UC-06",
        name="Member FAQ",
        persona="Visitor",
        brand="DentAssure",
        question="How do I find a clinic and what should I carry for my first visit?",
        follow_up="Who do I call if my card is not working?",
        expected_source="dentassure_member_faq.txt",
        expected_keywords=["clinic", "card", "888"],
        why_it_matters="Patients who are not members yet still need clear next steps.",
    ),
    UseCase(
        use_case_id="UC-07",
        name="Conversational follow-up",
        persona="Visitor",
        brand="DentAssure",
        question="What is the waiting period for root canal?",
        follow_up="And when is pre-authorization required?",
        expected_source="dentassure_policy_guide.pdf",
        expected_keywords=["90", "waiting", "pre-auth"],
        why_it_matters="People ask follow-ups, not isolated questions. Memory must stay grounded.",
    ),
    UseCase(
        use_case_id="UC-08",
        name="Network clinic finder",
        persona="Visitor",
        brand="DentAssure",
        question="Where is a DentAssure clinic in Hyderabad and what are the hours and rating?",
        follow_up="How far is it from Kothapet?",
        expected_source="clinic/public/list API",
        expected_keywords=["Hyderabad", "hours", "clinic"],
        why_it_matters="Same question as the public website clinic pages, with offline fallback.",
    ),
    UseCase(
        use_case_id="UC-09",
        name="Plan compare for treatments",
        persona="Visitor",
        brand="DentAssure",
        question="Root canal and scaling which is the best plan?",
        follow_up="i want checkup and teeth cleaning which plan",
        expected_source="compare-all-plans API",
        expected_keywords=["STANDARD STEER", "scaling", "root canal"],
        why_it_matters="Matches dentassureplans.co.in/compare-services for a treatment mix.",
    ),
    UseCase(
        use_case_id="UC-10",
        name="Out-of-knowledge refusal",
        persona="Visitor",
        brand="DentAssure",
        question="What is the CEO's personal mobile number and home address?",
        follow_up=None,
        expected_source="",
        expected_keywords=[],
        must_refuse=True,
        why_it_matters="The assistant must not invent PII, prices, or clinical advice.",
    ),
    UseCase(
        use_case_id="UC-11",
        name="Featured plans catalog",
        persona="Visitor",
        brand="DentAssure",
        question="What plans do you have?",
        follow_up="STANDARD STEER - Explain about this plan",
        expected_source="featured plans API",
        expected_keywords=["STEER", "SHIELD", "Smart Saver"],
        why_it_matters="Same catalog as Our Plans; named-plan follow-up uses the public plan-details API.",
    ),
]


def get_use_cases() -> list[UseCase]:
    return list(USE_CASES)


def get_use_case(use_case_id: str) -> UseCase | None:
    for item in USE_CASES:
        if item.use_case_id == use_case_id:
            return item
    return None


def match_use_case(question: str) -> UseCase | None:
    """Map a free-text question to a catalog use case when possible."""
    lowered = question.lower()
    scored: list[tuple[int, UseCase]] = []
    for item in USE_CASES:
        haystack = f"{item.name} {item.question} {item.follow_up or ''}".lower()
        overlap = sum(1 for token in lowered.split() if len(token) > 3 and token in haystack)
        if item.must_refuse and any(word in lowered for word in ("ceo", "home address")):
            overlap += 5
        if item.use_case_id == "UC-09" and any(
            word in lowered for word in ("root canal", "scaling", "implant", "rct")
        ):
            overlap += 8
        if item.use_case_id == "UC-08" and any(
            word in lowered for word in ("clinic", "hours", "hyderabad", "rating", "distance")
        ):
            overlap += 6
        if item.use_case_id == "UC-11" and any(
            word in lowered
            for word in ("what plans", "our plans", "featured", "explain about this plan", "standard steer")
        ):
            overlap += 8
        if item.use_case_id == "UC-04" and any(
            word in lowered
            for word in ("how to take", "denssure", "enroll", "standard secure", "complete care")
        ) and not any(word in lowered for word in ("root canal", "scaling", "rct", "clinic", "steer")):
            overlap += 6
        scored.append((overlap, item))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    best_score, best = scored[0]
    return best if best_score >= 3 else None
