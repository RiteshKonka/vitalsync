"""
mcp_server/tools/coach_tools.py
────────────────────────────────
Coach-layer tools: user profile, saved insights, action item tracking.
In production these would persist to a database.
For now, module-level dicts act as the store.
"""

from __future__ import annotations
import time
from typing import Any

# ── In-memory stores ──────────────────────────────────────────────

_user_profiles: dict[str, dict] = {}
_saved_insights: dict[str, list] = {}   # session_id → list of insights

# Default profile (used when no session-specific profile exists)
DEFAULT_PROFILE = {
    "name":        "Rohan",
    "age":         28,
    "weight_kg":   72,
    "height_cm":   175,
    "tdee_kcal":   2400,
    "resting_hr":  58,
    "hrv_baseline": 62,
    "goals":       ["improve recovery", "understand fatigue patterns"],
    "training_days": ["Tuesday", "Thursday", "Saturday"],
}


def get_user_profile(session_id: str = "default") -> dict[str, Any]:
    """
    Returns the user's health profile for a session.
    Used by the coach agent to personalise recommendations.
    """
    return _user_profiles.get(session_id, DEFAULT_PROFILE.copy())


def save_insight(
    session_id: str,
    headline: str,
    explanation: str,
    action_items: list[str],
    domains: list[str],
) -> dict[str, Any]:
    """
    Saves a coach insight to the session's history.
    Returns the saved record with a timestamp and ID.
    """
    if session_id not in _saved_insights:
        _saved_insights[session_id] = []

    record = {
        "id":           f"ins_{int(time.time())}",
        "timestamp":    time.time(),
        "headline":     headline,
        "explanation":  explanation,
        "action_items": action_items,
        "domains":      domains,
        "resolved":     False,
    }
    _saved_insights[session_id].append(record)
    return record


def get_saved_insights(session_id: str) -> list[dict[str, Any]]:
    """Returns all saved insights for a session."""
    return _saved_insights.get(session_id, [])


def mark_insight_resolved(session_id: str, insight_id: str) -> bool:
    """Marks an insight action item as resolved by the user."""
    for insight in _saved_insights.get(session_id, []):
        if insight["id"] == insight_id:
            insight["resolved"] = True
            return True
    return False