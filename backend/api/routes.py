"""
api/routes.py
─────────────
REST endpoints for the React frontend.

GET  /api/health                      - health check
GET  /api/domains                     - list domains + colors
GET  /api/data                        - all domains last-14-day snapshot
GET  /api/data/{domain}               - 90-day raw records
GET  /api/data/{domain}/weekly        - day-of-week averages (?metric=...)
GET  /api/data/{domain}/summary       - aggregate stats
GET  /api/session/{sid}               - past queries + responses
POST /api/session/{sid}/init          - create / touch session
DELETE /api/session/{sid}             - clear history
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

try:
    from ..mock_data.generator import get_data, get_weekly_pattern, get_domain_summary
except Exception:
    try:
        from backend.mock_data.generator import get_data, get_weekly_pattern, get_domain_summary
    except Exception:
        from mock_data.generator import get_data, get_weekly_pattern, get_domain_summary

try:
    from .session import get, get_or_create, cleanup_old
except Exception:
    from api.session import get, get_or_create, cleanup_old

logger = logging.getLogger(__name__)
router = APIRouter()

VALID_DOMAINS = {"sleep", "activity", "nutrition", "stress", "weather"}

DOMAIN_META = [
    {"id": "sleep",     "label": "Sleep",     "color": "#7F77DD", "key_metric": "deep_sleep_pct"},
    {"id": "activity",  "label": "Activity",  "color": "#D85A30", "key_metric": "training_load"},
    {"id": "nutrition", "label": "Nutrition", "color": "#BA7517", "key_metric": "caloric_balance"},
    {"id": "stress",    "label": "Stress",    "color": "#1D9E75", "key_metric": "resting_hr_bpm"},
    {"id": "weather",   "label": "Weather",   "color": "#378ADD", "key_metric": "temperature_c"},
]


# ── Domain data ───────────────────────────────────────────────────

@router.get("/data")
async def get_all_domains():
    """Last-14-day snapshot across all domains. Called on dashboard load."""
    return {
        d["id"]: {
            "recent":  get_data(d["id"])[-14:],
            "summary": get_domain_summary(d["id"]),
            "color":   d["color"],
        }
        for d in DOMAIN_META
    }


@router.get("/data/{domain}")
async def get_domain_data(domain: str):
    if domain not in VALID_DOMAINS:
        raise HTTPException(404, f"Unknown domain: {domain}")
    records = get_data(domain)
    return {"domain": domain, "records": records, "count": len(records)}


@router.get("/data/{domain}/weekly")
async def get_domain_weekly(domain: str, metric: str):
    if domain not in VALID_DOMAINS:
        raise HTTPException(404, f"Unknown domain: {domain}")
    try:
        pattern = get_weekly_pattern(domain, metric)
        return {"domain": domain, "metric": metric, "pattern": pattern}
    except Exception as e:
        raise HTTPException(400, str(e))


@router.get("/data/{domain}/summary")
async def get_domain_summary_route(domain: str):
    if domain not in VALID_DOMAINS:
        raise HTTPException(404, f"Unknown domain: {domain}")
    return get_domain_summary(domain)


# ── Domains metadata ──────────────────────────────────────────────

@router.get("/domains")
async def list_domains():
    return {"domains": DOMAIN_META}


# ── Session ───────────────────────────────────────────────────────

@router.post("/session/{session_id}/init")
async def init_session(session_id: str):
    s = get_or_create(session_id)
    return {
        "session_id":    s.session_id,
        "created_at":    s.created_at,
        "history_count": len(s.query_history),
    }


@router.get("/session/{session_id}")
async def get_session(session_id: str):
    s = get(session_id)
    if not s:
        return {"session_id": session_id, "history": [], "count": 0}
    return {"session_id": session_id, "history": s.query_history, "count": len(s.query_history)}


@router.delete("/session/{session_id}")
async def clear_session(session_id: str):
    s = get(session_id)
    if s:
        s.query_history.clear()
    return {"cleared": True}


@router.post("/admin/cleanup")
async def admin_cleanup():
    removed = cleanup_old()
    return {"removed_sessions": removed}