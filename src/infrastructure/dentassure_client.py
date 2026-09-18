"""Public DentAssure platform client. No auth token required."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from src.logging_setup import configure_logging

logger = configure_logging()

DEFAULT_BASE = "https://api.dentassureplans.co.in/v1"
TIMEOUT = 25


def api_base() -> str:
    return os.getenv("DENTASSURE_API_BASE", DEFAULT_BASE).rstrip("/")


def _request(method: str, path: str, payload: dict | None = None, params: dict | None = None) -> Any:
    url = api_base() + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "DentAssure-Knowledge-Assistant/1.0",
    }
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=body, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:400]
        logger.exception("DentAssure API %s %s failed: %s", method, path, detail)
        raise RuntimeError(f"DentAssure API {exc.code} on {path}") from exc
    except urllib.error.URLError as exc:
        logger.exception("DentAssure API unreachable")
        raise RuntimeError("DentAssure API is unreachable right now.") from exc


def search_treatments(search_text: str, limit: int = 8) -> list[dict[str, Any]]:
    data = _request(
        "GET",
        "/treatment/list",
        params={"limit": str(limit), "searchText": search_text},
    )
    return list(data.get("results") or [])


def compare_all_plans(treatments: list[dict[str, Any]], limit: int = 5) -> dict[str, Any]:
    return _request(
        "POST",
        "/master-plan-treatment/compare-all-plans",
        payload={"treatments": treatments, "compareMode": "withPremium"},
        params={"limit": str(limit), "skip": "0"},
    )


def list_clinics(search_text: str = "", limit: int = 30) -> list[dict[str, Any]]:
    data = _request(
        "POST",
        "/clinic/public/list",
        payload={"skip": 0, "limit": limit, "searchText": search_text or ""},
    )
    return list(data.get("data") or [])


def network_clinics() -> list[dict[str, Any]]:
    data = _request("GET", "/clinic/public/network-clinics")
    return list(data.get("data") or [])


def clinic_detail(clinic_id: str) -> dict[str, Any]:
    return _request("GET", f"/clinic/public/{clinic_id}")


def featured_plans(limit: int = 10) -> list[dict[str, Any]]:
    data = _request("GET", "/public/master-plans/featured", params={"limit": str(limit)})
    return list(data.get("data") or [])


def plan_details(slug: str) -> dict[str, Any]:
    """Public plan page payload. Slug example: standard-steer."""
    data = _request(
        "GET",
        f"/public/master-plans/{slug}/details",
        params={"displayLocation": "PLAN_DETAILS"},
    )
    return dict(data.get("data") or {})
