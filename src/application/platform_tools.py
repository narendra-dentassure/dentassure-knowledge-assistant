"""Live DentAssure tools with offline fixtures so the ZIP still works without the network."""

from __future__ import annotations

import json
import math
import os
import re
from dataclasses import dataclass
from typing import Any

from src.application.disclaimer import with_customer_care_notice
from src.config import PROJECT_ROOT
from src.infrastructure import dentassure_client as live
from src.logging_setup import configure_logging

logger = configure_logging()
FIXTURE_DIR = PROJECT_ROOT / "data" / "live_fixtures"

CITY_COORDS = {
    "hyderabad": (17.385044, 78.486671),
    "kothapet": (17.3665, 78.548),
    "nagol": (17.366488, 78.54446),
    "bengaluru": (12.9716, 77.5946),
    "bangalore": (12.9716, 77.5946),
}

# Informal English, Hinglish, and common clinic-counter spellings.
TREATMENT_ALIASES = [
    (r"\b(root\s*can(?:al|el)|rootcanal|rct|nerve\s*treatment)\b", "root canal"),
    (
        r"\b(dant\s*safai|daa?nt\s*safai|teeth?\s*clean(?:ing)?|tooth\s*clean(?:ing)?|"
        r"scal(?:e|ing)|cleaning|prophylaxis|plaque)\b",
        "scaling",
    ),
    (r"\b(implant|dummy\s*tooth|screw\s*tooth)\b", "implant"),
    (
        r"\b(op\s*consult(?:ation)?|opd|consultation|consult|check[\s-]*up|"
        r"doctor\s*(?:visit|see)|dentist\s*visit)\b",
        "OP Consultation",
    ),
    (r"\bop\b", "OP Consultation"),
    (r"\b(filling|cavity|cement\s*filling)\b", "filling"),
    (r"\b(crown|tooth\s*cap|cap)\b", "crown"),
    (r"\b(extraction|extract|nikalna|pull\s*tooth|remove\s*tooth|teeth\s*remove)\b", "extraction"),
]

COMMON_TYPOS = {
    "scalling": "scaling",
    "scalng": "scaling",
    "rootcanel": "rootcanal",
    "canel": "canal",
    "consultaton": "consultation",
    "consultion": "consultation",
    "consutation": "consultation",
    "chekcup": "checkup",
    "chekup": "checkup",
    "implent": "implant",
    "implants": "implant",
    "fillin": "filling",
    "filings": "filling",
    "extrction": "extraction",
    "kaunsa": "konsa",
    "kaun": "konsa",
}

PLAN_HINTS = (
    "which plan",
    "best plan",
    "should i buy",
    "plan should i",
    "compare",
    "cheapest",
    "buy",
    "which is best",
    "which one",
    "which take",
    "suggest",
    "recommend",
    "konsa",
    "lena",
    "batao",
    "batana",
    "sasta",
    "cheap",
    "package",
    "membership",
    "cover",
    "insurance",
    "budget",
    "kam paisa",
    "plan",
)

WANT_CARE_HINTS = (
    "i want",
    "i need",
    "want to",
    "need to",
    "i go",
    "going",
    "mujhe",
    "chahiye",
    "please",
    "take",
)

PLAN_SLUGS = [
    (r"\bstandard\s*steer\b|\bsteer\b|\bplan0052\b", "standard-steer"),
    (r"\bsmart\s*saver\b|\bplan0057\b", "smart-saver"),
    (r"\bsuperior\s*sparkle\b|\bplan0055\b", "superior-sparkle"),
    (r"\bsuperior\s*smile\b|\bplan0053\b", "superior-smile"),
    (r"\bsuperior\s*shield\b|\bplan0054\b", "superior-shield"),
    (r"\bstandard\s*simple\b|\bplan0049\b", "standard-simple"),
    (r"\bstandard\s*sensible\b|\bplan0050\b", "standard-sensible"),
    (r"\bstandard\s*secure\b|\bplan0051\b", "standard-secure"),
]

# Offline fixtures and live detail calls only for these slugs. Other named plans stay ungrounded.
DETAILED_PLAN_SLUGS = frozenset({"standard-steer", "superior-shield", "smart-saver"})

CATALOG_HINTS = (
    "our plans",
    "what plans",
    "which plans",
    "list of plans",
    "featured plan",
    "plans do you have",
    "available plans",
    "show plans",
    "all plans",
)

DEFINITION_HINTS = (
    "what is",
    "what are",
    "define",
    "meaning of",
    "explain",
)

PATIENT_COMPARE_EXAMPLES = [
    "If I want to go, OP consultation, scaling which plan should I buy?",
    "i want checkup and teeth cleaning which plan",
    "rct scaling konsa plan lena",
    "scalling and consultaton which take",
    "op and cleaning plan batao",
    "need implant and rct cheapest plan",
    "scaling checkup",
    "dant safai and doctor visit suggest",
]


@dataclass
class ToolAnswer:
    answer: str
    sources: list[dict[str, Any]]
    mode: str
    intent: str


def platform_mode() -> str:
    return os.getenv("PLATFORM_MODE", "auto").strip().lower()


def normalize_patient_text(question: str) -> str:
    """Lowercase, strip punctuation, and fix common clinic-counter typos."""
    text = question.lower().replace("’", "'")
    text = re.sub(r"[^a-z0-9\s]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    tokens = [COMMON_TYPOS.get(token, token) for token in text.split()]
    return " ".join(tokens)


def extract_plan_slug(question: str) -> str | None:
    """Map a named DentAssure plan to the public details slug, or None."""
    text = normalize_patient_text(question)
    for pattern, slug in PLAN_SLUGS:
        if re.search(pattern, text, flags=re.IGNORECASE):
            return slug
    return None


def classify_intent(question: str, history: str = "") -> str:
    text = normalize_patient_text(question)
    lookup = question
    if any(phrase in text for phrase in ("this plan", "that plan")) and not extract_plan_slug(question):
        lookup = f"{question} {history}"
    clinic_hit = any(
        word in text
        for word in (
            "clinic",
            "network",
            "hours",
            "open",
            "rating",
            "distance",
            "near",
            "location",
            "address",
            "phone",
            "mobile",
            "hyderabad",
            "kothapet",
            "nagol",
        )
    )
    treatments = extract_treatment_queries(question)
    plan_ask = any(phrase in text for phrase in PLAN_HINTS)
    want_care = any(phrase in text for phrase in WANT_CARE_HINTS)
    definition = any(phrase in text for phrase in DEFINITION_HINTS)
    compare_hit = bool(treatments) and (
        plan_ask or len(treatments) >= 2 or (want_care and not definition)
    )
    if definition and not plan_ask and len(treatments) < 2:
        compare_hit = False
    catalog_hit = (not treatments) and any(phrase in text for phrase in CATALOG_HINTS)
    slug = extract_plan_slug(lookup)
    if clinic_hit and compare_hit:
        return "both"
    if compare_hit:
        return "compare"
    if slug and slug in DETAILED_PLAN_SLUGS:
        return "plan_detail"
    if catalog_hit:
        return "catalog"
    if clinic_hit:
        return "clinic"
    return "docs"


def extract_treatment_queries(question: str) -> list[str]:
    text = normalize_patient_text(question)
    found: list[str] = []
    for pattern, query in TREATMENT_ALIASES:
        if re.search(pattern, text, flags=re.IGNORECASE) and query not in found:
            found.append(query)
    return found


def _load_json(name: str) -> Any:
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


def _use_live() -> bool:
    return platform_mode() in {"auto", "live"}


def _use_offline() -> bool:
    return platform_mode() in {"auto", "offline"}


SEARCH_ALIASES = {
    "scaling": "Scaling - Mild",
    "root canal": "Root canal",
}


def _rank_treatment_rows(query: str, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Prefer exact/short names; keep generic 'scaling' away from Deep Scaling."""
    needle = query.lower().strip()

    def score(row: dict[str, Any]) -> tuple:
        name = str(row.get("name") or "").lower()
        exact = 0 if name == needle else 1
        starts = 0 if name.startswith(needle) else 1
        extras = 0
        if "scaling" in needle and "deep" not in needle:
            extras += 0 if "mild" in name else 1
            extras += 2 if any(token in name for token in ("deep", "ems", "laser")) else 0
        return (exact, extras, starts, len(name))

    return sorted(rows, key=score)


def search_treatments(search_text: str) -> tuple[list[dict[str, Any]], str]:
    query = SEARCH_ALIASES.get(search_text.lower().strip(), search_text)
    if _use_live():
        try:
            rows = live.search_treatments(query)
            if rows:
                return _rank_treatment_rows(query, rows), "live"
        except Exception:
            logger.exception("Live treatment search failed; using fixtures")
            if platform_mode() == "live":
                raise
    fixtures = _load_json("treatments.json")["treatments"]
    tokens = [token for token in re.split(r"\s+", query.lower()) if token]
    matched = []
    for row in fixtures:
        blob = f"{row.get('name', '')} {row.get('code', '')}".lower()
        if query.lower() in blob or all(token in blob for token in tokens):
            matched.append(row)
    if not matched:
        return [], "offline"
    return _rank_treatment_rows(query, matched), "offline"


def list_clinics(search_text: str = "") -> tuple[list[dict[str, Any]], str]:
    if _use_live():
        try:
            rows = live.list_clinics(search_text)
            if rows:
                return rows, "live"
        except Exception:
            logger.exception("Live clinic list failed; using fixtures")
            if platform_mode() == "live":
                raise
    rows = _load_json("clinics.json")["data"]
    if search_text:
        needle = search_text.lower()
        rows = [
            row
            for row in rows
            if needle in json.dumps(row).lower()
        ]
    return rows, "offline"


def compare_plans(treatments: list[dict[str, Any]]) -> tuple[dict[str, Any], str]:
    if _use_live():
        try:
            return live.compare_all_plans(treatments), "live"
        except Exception:
            logger.exception("Live compare failed; using fixtures")
            if platform_mode() == "live":
                raise
    return _load_json("compare_default.json"), "offline"


def list_featured_plans() -> tuple[list[dict[str, Any]], str]:
    if _use_live():
        try:
            rows = live.featured_plans()
            if rows:
                compact = []
                for row in rows:
                    compact.append(
                        {
                            "code": row.get("code"),
                            "name": row.get("name"),
                            "premium": row.get("premium"),
                            "limit": row.get("limit"),
                            "type": row.get("type"),
                            "focus": ", ".join((row.get("planFeaturedTreatments") or [])[:4]),
                        }
                    )
                return compact, "live"
        except Exception:
            logger.exception("Live featured plans failed; using fixtures")
            if platform_mode() == "live":
                raise
    return list(_load_json("featured_plans.json")["plans"]), "offline"


def _inr(value: Any) -> str:
    try:
        return f"Rs {int(value):,}"
    except (TypeError, ValueError):
        return f"Rs {value}"


def _compact_plan_details(row: dict[str, Any], slug: str) -> dict[str, Any]:
    """Keep the public page fields chat needs; drop images, SEO, and 458-row dumps."""
    return {
        "name": row.get("name"),
        "price": row.get("price"),
        "coverageLimit": row.get("coverageLimit"),
        "description": str(row.get("description") or "").strip(),
        "planFeaturedTreatments": list(row.get("planFeaturedTreatments") or [])[:12],
        "keyBenefits": list(row.get("keyBenefits") or [])[:6],
        "pageUrl": f"https://dentassureplans.co.in/plan/{slug}/details",
        "totalTreatmentsInPlan": row.get("totalTreatmentsInPlan") or 0,
    }


def get_plan_details(slug: str) -> tuple[dict[str, Any] | None, str]:
    """Live plan page when the network works; three fixture slugs when offline."""
    if slug not in DETAILED_PLAN_SLUGS:
        return None, "offline"
    if _use_live():
        try:
            row = live.plan_details(slug)
            if row.get("name"):
                return _compact_plan_details(row, slug), "live"
        except Exception:
            logger.exception("Live plan details failed; using fixtures")
            if platform_mode() == "live":
                raise
    fixtures = _load_json("plan_details.json")
    if slug in fixtures:
        return dict(fixtures[slug]), "offline"
    return None, "offline"


def format_plan_detail_answer(plan: dict[str, Any], mode: str) -> str:
    treatments = plan.get("planFeaturedTreatments") or []
    benefits = plan.get("keyBenefits") or []
    extra = plan.get("totalTreatmentsInPlan") or 0
    lines = [
        f"**{plan.get('name')}** ({'live plan details API' if mode == 'live' else 'offline fixture'}):",
        f"Price: {_inr(plan.get('price'))} / year",
        f"Coverage limit: {_inr(plan.get('coverageLimit'))}",
        "",
    ]
    if plan.get("description"):
        lines.append(str(plan["description"]).strip())
        lines.append("")
    if treatments:
        lines.append("Featured treatments:")
        for item in treatments:
            lines.append(f"- {item}")
        lines.append("")
    if extra and extra > len(treatments):
        lines.append(f"Total treatments in this plan (public catalog): {extra}.")
        lines.append("")
    if benefits:
        lines.append("Key benefits:")
        for item in benefits:
            lines.append(f"- {item}")
        lines.append("")
    lines.append(f"Public page: {plan.get('pageUrl') or 'https://dentassureplans.co.in/our-plans'}")
    lines.append("For enrolment go to dentassureplans.co.in or a network clinic.")
    return with_customer_care_notice("\n".join(lines))


def format_catalog_answer(plans: list[dict[str, Any]], mode: str) -> str:
    lines = [
        f"DentAssure featured plans ({'live API' if mode == 'live' else 'offline fixture'}):",
        "Public catalog: https://dentassureplans.co.in/our-plans",
        "",
    ]
    for plan in plans:
        lines.append(
            f"- **{plan.get('name')}** ({plan.get('code')}): "
            f"Rs {plan.get('premium')} / year"
            + (f" — {plan.get('focus')}" if plan.get("focus") else "")
        )
    lines.append(
        "\nName the treatments you need (for example scaling and RCT) and I will rank a plan to buy. "
        "Public plan page (API): STANDARD STEER, SUPERIOR SHIELD, Smart Saver. "
        "Policy text (documents): STANDARD SECURE, COMPLETE CARE, Premium Dental Care. "
        "Other catalog names stay ungrounded. "
        "For enrolment go to dentassureplans.co.in or a network clinic."
    )
    return with_customer_care_notice("\n".join(lines))


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return round(2 * radius * math.asin(math.sqrt(a)), 1)


def _city_from_question(question: str) -> str | None:
    text = question.lower()
    for city in CITY_COORDS:
        if city in text:
            return city
    return None


def _format_address(address: Any) -> str:
    if isinstance(address, str):
        return address
    if not isinstance(address, dict):
        return ""
    parts = [
        address.get("addressLine1"),
        address.get("addressLine2"),
        address.get("city"),
        address.get("state"),
        address.get("zipCode"),
    ]
    return ", ".join(part for part in parts if part)


def format_clinic_answer(question: str, clinics: list[dict[str, Any]], mode: str) -> str:
    origin = _city_from_question(question)
    origin_xy = CITY_COORDS.get(origin or "", None)
    lines = [
        f"Network clinics ({'live DentAssure API' if mode == 'live' else 'offline sample directory'}):",
        "",
    ]
    if not clinics:
        return "No network clinic matched that city or name in the current source."
    for clinic in clinics[:8]:
        address = _format_address(clinic.get("address"))
        timings = clinic.get("timings") or {}
        today_hours = timings.get("Monday") or next(iter(timings.values()), "not listed")
        coords = clinic.get("coordinates") or {}
        distance = ""
        if origin_xy and coords.get("lat") and coords.get("lng"):
            km = haversine_km(origin_xy[0], origin_xy[1], float(coords["lat"]), float(coords["lng"]))
            distance = f"- Distance from {origin.title()}: about {km} km\n"
        rating = clinic.get("rating")
        reviews = clinic.get("reviewCount")
        rating_line = f"- Rating: {rating} ({reviews} reviews)" if rating else "- Rating: not published on the public card"
        phone = clinic.get("mobileNumber") or clinic.get("phone") or clinic.get("contactNote")
        lines.append(
            f"**{clinic.get('name')}**\n"
            f"- Address: {address or 'not listed'}\n"
            f"- Hours: {today_hours}\n"
            f"{distance}"
            f"{rating_line}\n"
            f"- Cashless: {'yes' if clinic.get('cashlessAvailable') else 'check at desk'}\n"
            f"- Phone: {phone or 'not on the public clinic API; use DentAssure support +91 888 668 6850'}\n"
            f"- Maps: {clinic.get('googleMapsUrl') or 'https://dentassureplans.co.in/our-network-clinics'}\n"
        )
    lines.append(
        "If you need distance from your exact pin, tell me the area (for example Kothapet or Nagol)."
    )
    return with_customer_care_notice("\n".join(lines))


def format_compare_answer(payload: dict[str, Any], mode: str, labels: list[str]) -> str:
    summary = payload.get("simpleSummary") or {}
    with_plan = summary.get("withPlan") or {}
    rec = summary.get("recommendation") or {}
    without = (summary.get("withoutPlan") or {}).get("totalAmount")
    top = payload.get("top5Plans") or payload.get("planComparisons") or []
    plan_name = with_plan.get("planName") or "the top ranked plan"
    plan_code = with_plan.get("planCode") or ""
    premium = with_plan.get("planPremium")
    total = with_plan.get("totalPatientCost")
    save = with_plan.get("netBenefit")
    lines = [
        f"**Buy this: {plan_name}" + (f" ({plan_code})" if plan_code else "") + "**",
        "",
        f"Treatments asked: {', '.join(labels)}",
        f"Pay Rs {total} with this plan (plan price Rs {premium}).",
        f"Without a plan you pay Rs {without}.",
    ]
    try:
        save_n = float(save) if save is not None else None
    except (TypeError, ValueError):
        save_n = None
    if save_n is not None and save_n >= 0:
        lines.append(f"You save about Rs {save} compared with paying cash.")
    elif save_n is not None:
        lines.append(
            "This visit alone may not fully recover the premium, but the plan covers many more treatments if you need them later."
        )
    lines.extend(
        [
            f"Why: {rec.get('reason') or rec.get('shouldBuyPlan') or 'Lowest total out-of-pocket for this mix.'}",
            "",
            f"Source: {'live compare-all-plans API' if mode == 'live' else 'offline fixture matching the public API'}.",
            "",
            "Other close plans:",
        ]
    )
    for plan in top[:5]:
        lines.append(
            f"- Rank {plan.get('rank')}: {plan.get('masterPlanName')} "
            f"premium Rs {plan.get('planPremium')}, "
            f"out-of-pocket Rs {plan.get('totalPatientCost')}, "
            f"net save Rs {plan.get('netSavingsAfterPremium')}"
        )
    lines.append(
        "\nRanking is total out-of-pocket (treatment + plan amount). Lower is better."
    )
    return with_customer_care_notice("\n".join(lines))


def try_platform_tools(question: str, history: str = "") -> ToolAnswer | None:
    """Answer clinic / compare / plan-detail questions from live API or fixtures."""
    try:
        return _try_platform_tools(question, history)
    except Exception:
        logger.exception("Platform tools failed")
        return None


def _try_platform_tools(question: str, history: str = "") -> ToolAnswer | None:
    """Answer clinic / compare / plan-detail questions from live API or fixtures."""
    intent = classify_intent(question, history)
    if intent == "docs":
        return None

    parts: list[str] = []
    sources: list[dict[str, Any]] = []
    mode_used = "offline"

    if intent == "plan_detail":
        slug = extract_plan_slug(question) or extract_plan_slug(f"{question} {history}")
        detail, mode_used = get_plan_details(slug) if slug else (None, "offline")
        if not detail:
            return None
        parts.append(format_plan_detail_answer(detail, mode_used))
        sources.append(
            {
                "source": "plan details API" if mode_used == "live" else "data/live_fixtures/plan_details.json",
                "page": 1,
                "score": 1.0,
                "snippet": f"Published DentAssure plan page for {detail.get('name')}.",
            }
        )

    if intent == "catalog":
        plans, mode_used = list_featured_plans()
        parts.append(format_catalog_answer(plans, mode_used))
        sources.append(
            {
                "source": "featured plans API" if mode_used == "live" else "data/live_fixtures/featured_plans.json",
                "page": 1,
                "score": 1.0,
                "snippet": "Published DentAssure plans from the public catalog.",
            }
        )

    if intent in {"compare", "both"}:
        queries = extract_treatment_queries(question) or ["OP Consultation"]
        selected: list[dict[str, Any]] = []
        labels: list[str] = []
        last_mode = "offline"
        for query in queries:
            rows, last_mode = search_treatments(query)
            if not rows:
                continue
            hit = rows[0]
            selected.append({"treatmentId": hit.get("id") or hit.get("treatmentId"), "quantity": 1})
            labels.append(f"{hit.get('code', '')} {hit.get('name', query)}".strip())
        if selected:
            payload, last_mode = compare_plans(selected)
            mode_used = last_mode
            parts.append(format_compare_answer(payload, last_mode, labels))
            sources.append(
                {
                    "source": "compare-all-plans API" if last_mode == "live" else "data/live_fixtures/compare_default.json",
                    "page": 1,
                    "score": 1.0,
                    "snippet": "Ranked by treatment cost + plan amount.",
                }
            )

    if intent in {"clinic", "both"}:
        city = _city_from_question(question) or ""
        clinics, clinic_mode = list_clinics(city)
        mode_used = clinic_mode if intent == "clinic" else mode_used
        parts.append(format_clinic_answer(question, clinics, clinic_mode))
        sources.append(
            {
                "source": "clinic/public/list API" if clinic_mode == "live" else "data/live_fixtures/clinics.json",
                "page": 1,
                "score": 1.0,
                "snippet": "Public network clinics, hours, ratings, cashless flag.",
            }
        )

    if not parts:
        return None
    return ToolAnswer(answer="\n\n".join(parts), sources=sources, mode=mode_used, intent=intent)
