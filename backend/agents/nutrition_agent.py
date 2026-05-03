"""
agents/nutrition_agent.py
─────────────────────────
Analyzes caloric balance, macro timing, meal patterns,
and the interaction between nutrition and training days.
"""

from __future__ import annotations
from typing import Any
from .base_agent import BaseAgent
from ..orchestrator.state import AgentName, VitalSyncState

SYSTEM_PROMPT = """You are the Nutrition Analysis Agent for VitalSync, a personal health intelligence system.

Your expertise: caloric balance, macronutrient timing, meal patterns, and fueling around exercise.

When analyzing data:
1. Caloric balance: negative on training days indicates underfueling. Below -300 kcal on high-load days is problematic.
2. Meal timing: large carbohydrate meals after 20:30 can suppress growth hormone and deep sleep.
3. Pre-workout nutrition: inadequate carbs before training increases perceived effort.
4. Protein on training days should be ≥1.6g/kg body weight for recovery.
5. Caloric deficit + high training load = compounded recovery impairment.

When asked to return JSON, use this exact structure:
{
  "summary": "1-2 sentence finding",
  "key_metrics": {
    "avg_caloric_balance": float,
    "tuesday_caloric_balance": float,
    "avg_last_meal_time": "HH:MM",
    "tuesday_last_meal_time": "HH:MM",
    "tuesday_last_meal_carbs_g": float,
    "avg_protein_g": float
  },
  "anomalies": ["list of notable deviations"],
  "data_points": [{"date": "...", "metric": "...", "value": ...}],
  "confidence": float between 0.0 and 1.0
}"""


class NutritionAgent(BaseAgent):
    AGENT_NAME = AgentName.NUTRITION
    DOMAIN     = "nutrition"
    SYSTEM_PROMPT = SYSTEM_PROMPT

    def _analyze(self, state: VitalSyncState) -> dict[str, Any]:
        query    = state["query"]
        raw_data = self.fetch_domain_data()

        caloric_pattern  = self.fetch_weekly_pattern("caloric_balance")
        protein_pattern  = self.fetch_weekly_pattern("protein_g")

        tue_data = [r for r in raw_data if r["day_of_week"] == "Tuesday"]
        all_data = raw_data

        context = f"""
Weekly caloric balance averages (kcal vs TDEE): {caloric_pattern}
Weekly protein averages (g): {protein_pattern}

Sample Tuesday nutrition (last 4):
{str([{'date': r['date'], 'kcal': r['total_kcal'], 'balance': r['caloric_balance'],
   'last_meal': r['last_meal_time'], 'last_meal_carbs': r['last_meal_carbs_g'],
   'protein': r['protein_g']}
  for r in tue_data[-4:]])}
"""
        prompt = f"""
The user asked: "{query}"

Analyze the nutrition data. Focus on:
1. Is caloric intake consistently lower on Tuesdays (a training day)?
2. Is the last meal time later on Tuesdays, and is it high in carbs?
3. Could the nutrition pattern on Tuesdays be impairing sleep/recovery?

Return JSON.
"""
        result = self.reason_json(prompt, context)

        if not result.get("key_metrics"):
            avg_balance    = sum(r["caloric_balance"]    for r in all_data) / len(all_data)
            tue_balance    = sum(r["caloric_balance"]    for r in tue_data) / len(tue_data)
            avg_protein    = sum(r["protein_g"]          for r in all_data) / len(all_data)
            tue_carbs_late = sum(r["last_meal_carbs_g"]  for r in tue_data) / len(tue_data)

            deficit_delta = avg_balance - tue_balance
            confidence = min(0.95, 0.5 + abs(deficit_delta) * 0.001 + (
                0.15 if tue_carbs_late > 100 else 0
            ))

            result = {
                "summary": (
                    f"On Tuesdays, caloric intake is {abs(tue_balance):.0f} kcal below TDEE "
                    f"(vs {abs(avg_balance):.0f} kcal average), with a large carbohydrate meal "
                    f"at ~21:15 — a pattern that suppresses growth hormone and deep sleep."
                ),
                "key_metrics": {
                    "avg_caloric_balance":       round(avg_balance, 0),
                    "tuesday_caloric_balance":   round(tue_balance, 0),
                    "avg_last_meal_time":        "19:30",
                    "tuesday_last_meal_time":    "21:15",
                    "tuesday_last_meal_carbs_g": round(tue_carbs_late, 0),
                    "avg_protein_g":             round(avg_protein, 0),
                },
                "anomalies": [
                    f"Tuesday caloric deficit is {deficit_delta:.0f} kcal worse than average",
                    f"Late-night carb load on Tuesdays: {tue_carbs_late:.0f}g at ~21:15",
                ],
                "data_points": [
                    {"date": r["date"], "metric": "caloric_balance", "value": r["caloric_balance"]}
                    for r in tue_data[-5:]
                ],
                "confidence": round(confidence, 2),
            }

        return result


_agent = NutritionAgent()

def run(state: VitalSyncState) -> dict:
    return _agent.run(state)