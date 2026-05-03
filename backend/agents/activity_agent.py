"""
agents/activity_agent.py
────────────────────────
Analyzes training load, workout intensity zones, step counts,
and weekly training distribution patterns.
"""

from __future__ import annotations
from typing import Any
from .base_agent import BaseAgent
from ..orchestrator.state import AgentName, VitalSyncState

SYSTEM_PROMPT = """You are the Activity Analysis Agent for VitalSync, a personal health intelligence system.

Your expertise: training load, exercise intensity zones, workout timing, weekly periodisation, overtraining detection.

When analyzing data:
1. Training load > 60 is high. > 75 is very high. Consecutive high-load days increase injury/fatigue risk.
2. Zone 3/4 minutes: cardiovascular stress indicator. > 45 min zone 3/4 in one session is significant.
3. Day-of-week patterns: is one day consistently overloaded vs others?
4. Training load should ideally follow a periodised pattern (hard/easy alternation).
5. Late evening workouts (after 20:00) can suppress sleep quality.

When asked to return JSON, use this exact structure:
{
  "summary": "1-2 sentence finding",
  "key_metrics": {
    "avg_training_load": float,
    "tuesday_training_load": float,
    "avg_zone34_minutes": float,
    "tuesday_zone34_minutes": float,
    "avg_workout_minutes": float,
    "tuesday_workout_minutes": float
  },
  "anomalies": ["list of notable deviations"],
  "data_points": [{"date": "...", "metric": "...", "value": ...}],
  "confidence": float between 0.0 and 1.0
}"""


class ActivityAgent(BaseAgent):
    AGENT_NAME = AgentName.ACTIVITY
    DOMAIN     = "activity"
    SYSTEM_PROMPT = SYSTEM_PROMPT

    def _analyze(self, state: VitalSyncState) -> dict[str, Any]:
        query    = state["query"]
        raw_data = self.fetch_domain_data()

        load_pattern    = self.fetch_weekly_pattern("training_load")
        zone34_pattern  = {
            day: round(
                sum(r["zone3_minutes"] + r["zone4_minutes"]
                    for r in raw_data if r["day_of_week"] == day)
                / max(1, sum(1 for r in raw_data if r["day_of_week"] == day)),
                1
            )
            for day in ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
        }
        workout_pattern = self.fetch_weekly_pattern("workout_minutes")

        context = f"""
Weekly training load averages: {load_pattern}
Weekly zone 3+4 minutes averages: {zone34_pattern}
Weekly workout duration averages (mins): {workout_pattern}

Sample Tuesday sessions (last 4):
{[{'date': r['date'], 'load': r['training_load'], 'workout_mins': r['workout_minutes'],
   'z3': r['zone3_minutes'], 'z4': r['zone4_minutes'], 'type': r['workout_type']}
  for r in raw_data if r['day_of_week'] == 'Tuesday'][-4:]}
"""
        prompt = f"""
The user asked: "{query}"

Analyze the activity data. Focus on:
1. Is Tuesday's training load significantly higher than other days?
2. How much zone 3/4 cardio happens on Tuesdays vs other days?
3. Is the training distribution well-periodised or is one day overloaded?

Return JSON.
"""
        result = self.reason_json(prompt, context)

        if not result.get("key_metrics"):
            tue  = [r for r in raw_data if r["day_of_week"] == "Tuesday"]
            all_ = [r for r in raw_data if r["training_load"] > 0]

            avg_load   = sum(r["training_load"] for r in all_) / len(all_)
            tue_load   = sum(r["training_load"] for r in tue)  / len(tue)
            avg_z34    = sum(r["zone3_minutes"] + r["zone4_minutes"] for r in all_) / len(all_)
            tue_z34    = sum(r["zone3_minutes"] + r["zone4_minutes"] for r in tue)  / len(tue)
            avg_mins   = sum(r["workout_minutes"] for r in all_) / len(all_)
            tue_mins   = sum(r["workout_minutes"] for r in tue)  / len(tue)
            ratio      = tue_load / avg_load if avg_load else 1

            confidence = min(0.95, 0.45 + (ratio - 1) * 0.5)

            result = {
                "summary": (
                    f"Tuesday training load ({tue_load:.0f}) is {ratio:.1f}× the weekly average "
                    f"({avg_load:.0f}), with {tue_z34:.0f} minutes in zones 3–4 — "
                    f"the highest-intensity day of the week."
                ),
                "key_metrics": {
                    "avg_training_load":       round(avg_load, 1),
                    "tuesday_training_load":   round(tue_load, 1),
                    "avg_zone34_minutes":      round(avg_z34, 1),
                    "tuesday_zone34_minutes":  round(tue_z34, 1),
                    "avg_workout_minutes":     round(avg_mins, 1),
                    "tuesday_workout_minutes": round(tue_mins, 1),
                },
                "anomalies": [
                    f"Tuesday load is {ratio:.1f}× the weekly average",
                    f"Tuesday has {tue_z34 - avg_z34:.0f} more zone 3/4 minutes than average",
                ],
                "data_points": [
                    {"date": r["date"], "metric": "training_load", "value": r["training_load"]}
                    for r in tue[-5:]
                ],
                "confidence": round(confidence, 2),
            }

        return result


_agent = ActivityAgent()

def run(state: VitalSyncState) -> dict:
    return _agent.run(state)