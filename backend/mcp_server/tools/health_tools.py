"""
mcp_server/tools/health_tools.py
─────────────────────────────────
Health data tool functions registered on the MCP server.
Each function is a pure data accessor — no LLM logic here.
Agents call these via the MCP protocol; swapping mock → real
wearable API only requires changing these functions.
"""

from __future__ import annotations
from typing import Any
try:
    from ...mock_data.generator import get_data, get_weekly_pattern, get_domain_summary
except Exception:
    try:
        from backend.mock_data.generator import get_data, get_weekly_pattern, get_domain_summary
    except Exception:
        from mock_data.generator import get_data, get_weekly_pattern, get_domain_summary


def get_sleep_data() -> list[dict[str, Any]]:
    """
    Returns 90 days of sleep records.
    Fields: date, day_of_week, total_hours, deep_sleep_pct,
    light_sleep_pct, rem_sleep_pct, hrv_ms, sleep_score,
    sleep_start, wake_time.
    """
    return get_data("sleep")


def get_activity_data() -> list[dict[str, Any]]:
    """
    Returns 90 days of activity records.
    Fields: date, day_of_week, steps, workout_minutes,
    zone1_minutes, zone3_minutes, zone4_minutes,
    calories_burned, training_load, workout_type.
    """
    return get_data("activity")


def get_nutrition_data() -> list[dict[str, Any]]:
    """
    Returns 90 days of nutrition records.
    Fields: date, day_of_week, total_kcal, protein_g,
    carbs_g, fat_g, meal_count, last_meal_time,
    last_meal_carbs_g, caloric_balance, hydration_ml.
    """
    return get_data("nutrition")


def get_stress_data() -> list[dict[str, Any]]:
    """
    Returns 90 days of stress/recovery records.
    Fields: date, day_of_week, resting_hr_bpm,
    hrv_morning_ms, recovery_score, stress_level, autonomic_balance.
    """
    return get_data("stress")


def get_weekly_pattern_tool(domain: str, metric: str) -> dict[str, float]:
    """
    Returns day-of-week averages for any domain metric.
    Example: domain='sleep', metric='deep_sleep_pct'
    Returns: {'Monday': 22.1, 'Tuesday': 11.9, ...}
    """
    return get_weekly_pattern(domain, metric)


def get_domain_summary_tool(domain: str) -> dict[str, Any]:
    """
    Returns aggregate statistics and day-of-week patterns for a domain.
    Valid domains: sleep, activity, nutrition, stress, weather.
    """
    return get_domain_summary(domain)


def get_all_domains_summary() -> dict[str, Any]:
    """
    Returns a quick summary across all 5 domains in one call.
    Used by the correlator to get a broad overview before deep analysis.
    """
    domains = ["sleep", "activity", "nutrition", "stress", "weather"]
    return {d: get_domain_summary(d) for d in domains}