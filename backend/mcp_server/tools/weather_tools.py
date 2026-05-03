"""
mcp_server/tools/weather_tools.py
──────────────────────────────────
Weather tool — tries Open-Meteo (free, no API key) first,
falls back to mock data if the network is unavailable.
"""

from __future__ import annotations
import logging
from datetime import date, timedelta
from typing import Any

import httpx

try:
    from ...mock_data.generator import get_data
except Exception:
    try:
        from backend.mock_data.generator import get_data
    except Exception:
        from mock_data.generator import get_data

logger = logging.getLogger(__name__)

LATITUDE  = 19.0760   # Mumbai
LONGITUDE = 72.8777
DAYS_OF_WEEK = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def _fetch_open_meteo(days: int = 90) -> list[dict[str, Any]] | None:
    """Calls the Open-Meteo historical archive API. Returns None on any failure."""
    end_date   = date.today() - timedelta(days=1)   # yesterday (archive lag)
    start_date = end_date - timedelta(days=days - 1)

    url = (
        "https://archive-api.open-meteo.com/v1/archive"
        f"?latitude={LATITUDE}&longitude={LONGITUDE}"
        f"&start_date={start_date}&end_date={end_date}"
        "&daily=temperature_2m_mean,precipitation_sum,"
        "relative_humidity_2m_mean,pressure_msl_mean,windspeed_10m_max"
        "&timezone=Asia%2FKolkata"
    )
    try:
        resp = httpx.get(url, timeout=8.0)
        resp.raise_for_status()
        raw = resp.json()
        daily = raw.get("daily", {})

        records = []
        for i, d in enumerate(daily.get("time", [])):
            parsed = date.fromisoformat(d)
            records.append({
                "date":             d,
                "day_of_week":      DAYS_OF_WEEK[parsed.weekday()],
                "temperature_c":    daily["temperature_2m_mean"][i],
                "precipitation_mm": daily["precipitation_sum"][i] or 0.0,
                "humidity_pct":     (daily.get("relative_humidity_2m_mean") or [65]*days)[i],
                "pressure_hpa":     (daily.get("pressure_msl_mean") or [1013]*days)[i],
                "windspeed_kmh":    (daily.get("windspeed_10m_max") or [10]*days)[i],
                "condition": (
                    "rainy"  if (daily["precipitation_sum"][i] or 0) > 3 else
                    "cloudy" if (daily["precipitation_sum"][i] or 0) > 0.5 else
                    "sunny"
                ),
            })
        logger.info("Open-Meteo: fetched %d days of real weather data", len(records))
        return records
    except Exception as e:
        logger.warning("Open-Meteo unavailable (%s), using mock weather", e)
        return None


def get_weather_data() -> list[dict[str, Any]]:
    """
    Returns 90 days of weather data.
    Uses real Open-Meteo data when available, mock data as fallback.
    Fields: date, day_of_week, temperature_c, precipitation_mm,
    humidity_pct, pressure_hpa, windspeed_kmh, condition.
    """
    return _fetch_open_meteo() or get_data("weather")


def get_weather_weekly_pattern() -> dict[str, dict[str, float]]:
    """
    Returns day-of-week averages for all weather metrics.
    Useful for quick correlation checks without fetching all 90 rows.
    """
    records = get_weather_data()
    from collections import defaultdict

    buckets: dict[str, dict[str, list]] = {
        day: {"temperature_c": [], "precipitation_mm": [], "humidity_pct": []}
        for day in DAYS_OF_WEEK
    }
    for r in records:
        day = r["day_of_week"]
        if day in buckets:
            for metric in ["temperature_c", "precipitation_mm", "humidity_pct"]:
                buckets[day][metric].append(r[metric])

    return {
        day: {
            metric: round(sum(vals) / len(vals), 2) if vals else 0.0
            for metric, vals in metrics.items()
        }
        for day, metrics in buckets.items()
    }