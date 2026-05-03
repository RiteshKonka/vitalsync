"""
agents/sleep_agent.py
─────────────────────
Analyzes sleep stages, HRV, deep sleep percentage, and timing patterns.
Specialises in detecting day-of-week anomalies in sleep quality.
"""

from __future__ import annotations
from typing import Any
from .base_agent import BaseAgent
from ..orchestrator.state import AgentName, VitalSyncState

SYSTEM_PROMPT = """You are the Sleep Analysis Agent for VitalSync, a personal health intelligence system.

Your expertise: sleep architecture, HRV during sleep, deep sleep quality, sleep timing, and recovery.

When analyzing data:
1. Look for day-of-week patterns — does sleep quality vary by day?
2. Compare deep sleep % against the 22% baseline. Below 15% is a significant anomaly.
3. HRV during sleep: below 44ms is poor, 44-60ms is moderate, above 60ms is good.
4. Late sleep start times (after 23:00) correlate with reduced deep sleep.
5. Calculate confidence based on how consistent and strong the pattern is.

When asked to return JSON, use this exact structure:
{
  "summary": "1-2 sentence finding",
  "key_metrics": {
    "avg_deep_sleep_pct": float,
    "tuesday_deep_sleep_pct": float,
    "avg_hrv_ms": float,
    "tuesday_hrv_ms": float,
    "avg_sleep_hours": float
  },
  "anomalies": ["list of notable deviations"],
  "data_points": [{"date": "...", "metric": "...", "value": ...}],
  "confidence": float between 0.0 and 1.0
}"""


class SleepAgent(BaseAgent):
    AGENT_NAME = AgentName.SLEEP
    DOMAIN     = "sleep"
    SYSTEM_PROMPT = SYSTEM_PROMPT

    def _analyze(self, state: VitalSyncState) -> dict[str, Any]:
        query = state["query"]

        # Fetch data via MCP tools
        raw_data = self.fetch_domain_data()
        deep_pattern   = self.fetch_weekly_pattern("deep_sleep_pct")
        hrv_pattern    = self.fetch_weekly_pattern("hrv_ms")
        hours_pattern  = self.fetch_weekly_pattern("total_hours")

        # Build compact context for LLM (avoid sending 90 full rows)
        context = f"""
Weekly deep sleep averages (%): {deep_pattern}
Weekly HRV averages (ms): {hrv_pattern}
Weekly sleep hours averages: {hours_pattern}

Sample Tuesday nights (last 4):
{[r for r in raw_data if r['day_of_week'] == 'Tuesday'][-4:]}

Sample Wednesday mornings context (last 4 Tuesday records showing sleep_score):
{[{'date': r['date'], 'deep_pct': r['deep_sleep_pct'], 'hrv': r['hrv_ms'], 'score': r['sleep_score']}
  for r in raw_data if r['day_of_week'] == 'Tuesday'][-4:]}
"""
        analysis_prompt = f"""
The user asked: "{query}"

Analyze the sleep data above. Focus on:
1. Is there a Tuesday-night pattern in deep sleep % or HRV?
2. How does Tuesday compare to the weekly average?
3. Are there any other notable anomalies?

Return your findings as JSON.
"""
        result = self.reason_json(analysis_prompt, context)

        # If LLM returned empty/bad JSON, compute fallback from raw data
        if not result.get("key_metrics"):
            tue_data  = [r for r in raw_data if r["day_of_week"] == "Tuesday"]
            all_data  = raw_data

            avg_deep  = sum(r["deep_sleep_pct"] for r in all_data)  / len(all_data)
            tue_deep  = sum(r["deep_sleep_pct"] for r in tue_data)  / len(tue_data)
            avg_hrv   = sum(r["hrv_ms"]         for r in all_data)  / len(all_data)
            tue_hrv   = sum(r["hrv_ms"]         for r in tue_data)  / len(tue_data)
            avg_hours = sum(r["total_hours"]     for r in all_data)  / len(all_data)

            delta_deep = avg_deep - tue_deep
            confidence = min(0.95, 0.5 + delta_deep * 0.025)

            result = {
                "summary": (
                    f"Tuesday nights show significantly reduced deep sleep "
                    f"({tue_deep:.1f}% vs {avg_deep:.1f}% average) and lower HRV "
                    f"({tue_hrv:.1f}ms vs {avg_hrv:.1f}ms average), indicating poor recovery."
                ),
                "key_metrics": {
                    "avg_deep_sleep_pct":     round(avg_deep, 1),
                    "tuesday_deep_sleep_pct": round(tue_deep, 1),
                    "avg_hrv_ms":             round(avg_hrv, 1),
                    "tuesday_hrv_ms":         round(tue_hrv, 1),
                    "avg_sleep_hours":        round(avg_hours, 1),
                },
                "anomalies": [
                    f"Deep sleep drops {delta_deep:.1f}pp on Tuesday nights",
                    f"HRV is {avg_hrv - tue_hrv:.1f}ms lower on Tuesday nights",
                ],
                "data_points": [
                    {"date": r["date"], "metric": "deep_sleep_pct", "value": r["deep_sleep_pct"]}
                    for r in tue_data[-5:]
                ],
                "confidence": round(confidence, 2),
            }

        return result


# LangGraph node function
_agent = SleepAgent()

def run(state: VitalSyncState) -> dict:
    return _agent.run(state)