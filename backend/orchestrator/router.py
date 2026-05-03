"""Decide which agents to activate based on query content."""
from typing import List


def select_agents_for_query(query: str) -> List[str]:
    q = query.lower()
    agents = []
    if "sleep" in q or "insomnia" in q:
        agents.append("sleep")
    if "train" in q or "activity" in q or "run" in q:
        agents.append("activity")
    if "eat" in q or "calorie" in q or "nutrition" in q:
        agents.append("nutrition")
    if not agents:
        agents = ["correlator", "coach"]
    return agents
