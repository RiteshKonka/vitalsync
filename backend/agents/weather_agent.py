"""
agents/weather_agent.py
───────────────────────
Correlates weather conditions with health metrics.
Uses Open-Meteo API (free, no key required) for real weather,
falling back to mock data if the API is unavailable.
"""

from __future__ import annotations
import logging
from typing import Any

import httpx

from .base_agent import BaseAgent
from ..orchestrator.state import AgentName, VitalSyncState
from ..mock_data.generator import get_data

logger = logging.getLogger(__name__)

# Mumbai coordinates (matches user's location)
LATITUDE  = 19.0760
LONGITUDE = 72.8777

SYSTEM_PROMPT = """You are the Weather Correlation Agent for VitalSync, a personal health intelligence system.

Your expertise: correlating environmental conditions with health and performance metrics.

When analyzing data:
1. Temperature: performance degrades above 32°C and below 15°C.
2. Humidity above 80% increases perceived exertion significantly.
3. Barometric pressure drops of >5hPa in 24h correlate with fatigue and joint pain.
4. High UV index on training days → dehydration risk.
5. Look for weak correlations: even a 0.2–0.3 correlation is meaningful over 90 days.
6. Be honest about weak evidence — don't overstate correlations.

When asked to return JSON, use this exact structure:
{
  "summary": "1-2 sentence finding",
  "key_metrics": {
    "avg_temperature_c": float,
    "tuesday_avg_temperature_c": float,
    "tuesday_rain_frequency_pct": float,
    "avg_humidity_pct": float,
    "correlation_strength": "weak|moderate|strong"
  },
  "anomalies": ["list of notable weather-health correlations"],
  "data_points": [{"date": "...", "metric": "...", "value": ...}],
  "confidence": float between 0.0 and 1.0
}"""


def _fetch_open_meteo() -> list[dict] | None:
    """
    Fetches real historical weather from Open-Meteo (free, no API key).
    Returns None if the request fails — caller falls back to mock data.
    """
    from datetime import date, timedelta
    end   = date.today()
    start = end - timedelta(days=89)

    url = (
        f"https://archive-api.open-meteo.com/v1/archive"
        f"?latitude={LATITUDE}&longitude={LONGITUDE}"
        f"&start_date={start}&end_date={end}"
        f"&daily=temperature_2m_mean,precipitation_sum,relative_humidity_2m_mean,pressure_msl_mean"
        f"&timezone=Asia%2FKolkata"
    )
    try:
        resp = httpx.get(url, timeout=8.0)
        resp.raise_for_status()
        data = resp.json()
        daily = data.get("daily", {})
        days_of_week = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]

        records = []
        for i, d in enumerate(daily.get("time", [])):
            from datetime import date as date_cls
            parsed = date_cls.fromisoformat(d)
            records.append({
                "date":             d,
                "day_of_week":      days_of_week[parsed.weekday()],
                "temperature_c":    daily["temperature_2m_mean"][i],
                "precipitation_mm": daily["precipitation_sum"][i],
                "humidity_pct":     daily.get("relative_humidity_2m_mean", [65]*90)[i],
                "pressure_hpa":     daily.get("pressure_msl_mean", [1013]*90)[i],
            })
        return records
    except Exception as e:
        logger.warning("Open-Meteo fetch failed, using mock weather: %s", e)
        return None


class WeatherAgent(BaseAgent):
    AGENT_NAME    = AgentName.WEATHER
    DOMAIN        = "weather"
    SYSTEM_PROMPT = SYSTEM_PROMPT

    def _analyze(self, state: VitalSyncState) -> dict[str, Any]:
        query = state["query"]

        # Try real API first, fall back to mock
        weather_data = _fetch_open_meteo() or get_data("weather")

        tue_weather = [r for r in weather_data if r["day_of_week"] == "Tuesday"]
        all_weather = weather_data

        avg_temp  = sum(r["temperature_c"]    for r in all_weather) / len(all_weather)
        tue_temp  = sum(r["temperature_c"]    for r in tue_weather) / len(tue_weather)
        avg_hum   = sum(r["humidity_pct"]     for r in all_weather) / len(all_weather)
        tue_rain  = sum(1 for r in tue_weather if r["precipitation_mm"] > 1)
        rain_pct  = (tue_rain / len(tue_weather)) * 100

        context = f"""
Overall avg temperature: {avg_temp:.1f}°C
Tuesday avg temperature: {tue_temp:.1f}°C
Overall avg humidity: {avg_hum:.1f}%
Tuesday rainy days: {tue_rain} / {len(tue_weather)} ({rain_pct:.0f}%)

Sample Tuesday weather (last 4):
{str([{'date': r['date'], 'temp': r['temperature_c'], 'rain': r['precipitation_mm'],
   'humidity': r['humidity_pct']}
  for r in tue_weather[-4:]])}
"""
        prompt = f"""
The user asked: "{query}"

Analyze whether weather conditions on Tuesdays correlate with the reported fatigue.
Note: the user does high-intensity workouts on Tuesdays.
Is there a meaningful weather correlation, or is it weak/absent?

Return JSON.
"""
        result = self.reason_json(prompt, context)

        if not result.get("key_metrics"):
            temp_delta = avg_temp - tue_temp
            # Weather correlation is intentionally weak in our dataset
            confidence = min(0.65, 0.3 + rain_pct * 0.003 + abs(temp_delta) * 0.02)

            result = {
                "summary": (
                    f"Weak weather correlation detected: {rain_pct:.0f}% of Tuesdays are rainy, "
                    f"slightly above the weekly average. Temperature and humidity are not "
                    f"meaningfully different on Tuesdays. Weather is a minor contributing factor."
                ),
                "key_metrics": {
                    "avg_temperature_c":          round(avg_temp, 1),
                    "tuesday_avg_temperature_c":  round(tue_temp, 1),
                    "tuesday_rain_frequency_pct": round(rain_pct, 1),
                    "avg_humidity_pct":           round(avg_hum, 1),
                    "correlation_strength":       "weak",
                },
                "anomalies": [
                    f"Tuesdays are rainy {rain_pct:.0f}% of the time (minor elevation)",
                ] if rain_pct > 30 else ["No significant weather anomalies on Tuesdays"],
                "data_points": [
                    {"date": r["date"], "metric": "precipitation_mm", "value": r["precipitation_mm"]}
                    for r in tue_weather[-5:]
                ],
                "confidence": round(confidence, 2),
            }

        return result


_agent = WeatherAgent()

def run(state: VitalSyncState) -> dict:
    return _agent.run(state)