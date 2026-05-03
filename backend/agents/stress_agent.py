"""
agents/stress_agent.py
──────────────────────
Analyzes resting heart rate, morning HRV, autonomic recovery,
and stress indicators across the week.
"""

from __future__ import annotations
from typing import Any
from .base_agent import BaseAgent
from ..orchestrator.state import AgentName, VitalSyncState

SYSTEM_PROMPT = """You are the Stress & Recovery Analysis Agent for VitalSync, a personal health intelligence system.

Your expertise: autonomic nervous system recovery, resting heart rate trends, morning HRV, and stress biomarkers.

When analyzing data:
1. Resting HR: 8+ bpm above personal baseline is a significant recovery flag.
2. Morning HRV: below 50ms suggests sympathetic dominance (stress/under-recovery).
3. Recovery score < 50 indicates the body is not ready for high-intensity training.
4. Sympathetic dominance on consecutive mornings indicates cumulative under-recovery.
5. High resting HR + low HRV = classic overreaching pattern.

When asked to return JSON, use this exact structure:
{
  "summary": "1-2 sentence finding",
  "key_metrics": {
    "avg_resting_hr": float,
    "wednesday_resting_hr": float,
    "avg_hrv_morning": float,
    "wednesday_hrv_morning": float,
    "avg_recovery_score": float,
    "wednesday_recovery_score": float
  },
  "anomalies": ["list of notable deviations"],
  "data_points": [{"date": "...", "metric": "...", "value": ...}],
  "confidence": float between 0.0 and 1.0
}"""


class StressAgent(BaseAgent):
    AGENT_NAME = AgentName.STRESS
    DOMAIN     = "stress"
    SYSTEM_PROMPT = SYSTEM_PROMPT

    def _analyze(self, state: VitalSyncState) -> dict[str, Any]:
        query    = state["query"]
        raw_data = self.fetch_domain_data()

        hr_pattern       = self.fetch_weekly_pattern("resting_hr_bpm")
        hrv_pattern      = self.fetch_weekly_pattern("hrv_morning_ms")
        recovery_pattern = self.fetch_weekly_pattern("recovery_score")

        wed_data = [r for r in raw_data if r["day_of_week"] == "Wednesday"]
        all_data = raw_data

        context = f"""
Weekly resting HR averages (bpm): {hr_pattern}
Weekly morning HRV averages (ms): {hrv_pattern}
Weekly recovery score averages: {recovery_pattern}

Sample Wednesday mornings (last 4) — the day after Tuesday training:
{str([{'date': r['date'], 'resting_hr': r['resting_hr_bpm'], 'hrv': r['hrv_morning_ms'],
   'recovery': r['recovery_score'], 'autonomic': r['autonomic_balance']}
  for r in wed_data[-4:]])}
"""
        prompt = f"""
The user asked: "{query}"

Analyze the stress/recovery data. Focus on:
1. Is Wednesday morning resting HR elevated compared to other days?
2. Is morning HRV lower on Wednesdays, indicating incomplete recovery?
3. Does the recovery score pattern match the fatigue complaint?

Return JSON.
"""
        result = self.reason_json(prompt, context)

        if not result.get("key_metrics"):
            avg_hr     = sum(r["resting_hr_bpm"]   for r in all_data) / len(all_data)
            wed_hr     = sum(r["resting_hr_bpm"]   for r in wed_data) / len(wed_data)
            avg_hrv    = sum(r["hrv_morning_ms"]   for r in all_data) / len(all_data)
            wed_hrv    = sum(r["hrv_morning_ms"]   for r in wed_data) / len(wed_data)
            avg_rec    = sum(r["recovery_score"]   for r in all_data) / len(all_data)
            wed_rec    = sum(r["recovery_score"]   for r in wed_data) / len(wed_data)

            hr_delta   = wed_hr - avg_hr
            confidence = min(0.95, 0.5 + hr_delta * 0.04 + (avg_hrv - wed_hrv) * 0.01)

            result = {
                "summary": (
                    f"Wednesday morning resting HR is {hr_delta:.0f}bpm above baseline "
                    f"({wed_hr:.0f} vs {avg_hr:.0f} avg), with HRV at {wed_hrv:.0f}ms "
                    f"({avg_hrv - wed_hrv:.0f}ms below average) — indicating the body "
                    f"has not recovered from Tuesday's training load."
                ),
                "key_metrics": {
                    "avg_resting_hr":           round(avg_hr, 1),
                    "wednesday_resting_hr":     round(wed_hr, 1),
                    "avg_hrv_morning":          round(avg_hrv, 1),
                    "wednesday_hrv_morning":    round(wed_hrv, 1),
                    "avg_recovery_score":       round(avg_rec, 1),
                    "wednesday_recovery_score": round(wed_rec, 1),
                },
                "anomalies": [
                    f"Wednesday resting HR is {hr_delta:.0f}bpm above average",
                    f"Wednesday morning HRV is {avg_hrv - wed_hrv:.0f}ms below average",
                    f"Recovery score drops to {wed_rec:.0f} on Wednesdays (avg: {avg_rec:.0f})",
                ],
                "data_points": [
                    {"date": r["date"], "metric": "resting_hr_bpm", "value": r["resting_hr_bpm"]}
                    for r in wed_data[-5:]
                ],
                "confidence": round(confidence, 2),
            }

        return result


_agent = StressAgent()

def run(state: VitalSyncState) -> dict:
    return _agent.run(state)