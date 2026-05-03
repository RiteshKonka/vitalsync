"""
orchestrator/supervisor.py
──────────────────────────
The supervisor is the orchestrator brain. It runs at graph entry and
again on every retry loop. It has two distinct jobs:

  Round 0 (first pass):
    - Parse the user's query using an LLM call to understand intent
    - Decide which domain agents are relevant (all 5, or a subset)
    - Emit a stream event so the frontend knows which agents will run

  Round N (retry, should_retry=True):
    - Look at which agents had confidence < CONFIDENCE_THRESHOLD
    - Re-activate only those agents, with an augmented query asking them
      to dig deeper into their specific finding
    - Increment retry_round counter

The supervisor uses the Groq LLM for query parsing — a lightweight
structured output call, not a reasoning chain. The real reasoning
happens inside each domain agent.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from .state import (
    VitalSyncState,
    AgentName,
    AgentStatus,
    StreamEvent,
    StreamEventType,
    CONFIDENCE_THRESHOLD,
)
from ..utils.groq_client import get_groq_client

logger = logging.getLogger(__name__)

# Agents the supervisor can activate (excludes correlator/coach — those
# are wired directly in the graph, not dispatched by supervisor)
DISPATCHABLE_AGENTS = [
    AgentName.SLEEP,
    AgentName.ACTIVITY,
    AgentName.NUTRITION,
    AgentName.STRESS,
    AgentName.WEATHER,
]

# Domain keywords used as a fast-path fallback if LLM parse fails
DOMAIN_KEYWORDS: dict[AgentName, list[str]] = {
    AgentName.SLEEP:      ["sleep", "tired", "fatigue", "exhausted", "rest", "hrv", "deep sleep", "insomnia"],
    AgentName.ACTIVITY:   ["workout", "exercise", "training", "steps", "cardio", "gym", "run", "active"],
    AgentName.NUTRITION:  ["eat", "food", "calories", "diet", "nutrition", "meal", "macro", "protein", "carb"],
    AgentName.STRESS:     ["stress", "anxious", "heart rate", "recovery", "resting hr", "tense"],
    AgentName.WEATHER:    ["weather", "rain", "cold", "hot", "season", "temperature", "barometric"],
}


# ─────────────────────────────────────────────
# Query parser
# ─────────────────────────────────────────────

PARSE_SYSTEM_PROMPT = """You are the orchestrator for a personal health analytics system.
Your job is to parse a user's health query and decide which specialist agents to activate.

Available agents:
- sleep: analyzes sleep stages, HRV, deep sleep percentage, sleep timing
- activity: analyzes workout load, training zones, step counts, weekly patterns
- nutrition: analyzes caloric balance, macro timing, meal patterns
- stress: analyzes resting heart rate, HRV trends, autonomic recovery
- weather: analyzes weather correlation with health metrics

Rules:
1. For broad queries ("why do I feel bad"), activate ALL agents.
2. For specific queries ("my sleep quality"), activate the most relevant 2-3 agents
   plus any agents likely to be correlated.
3. Always include weather if the user mentions patterns over time (days of week, seasons).
4. Return ONLY valid JSON, no prose, no markdown.

Return format:
{
  "agents": ["sleep", "activity"],   // subset of the 5 agent names
  "focus": "brief rephrasing of what each agent should look for",
  "reasoning": "one sentence explaining your selection"
}"""


def parse_query_with_llm(query: str) -> dict[str, Any]:
    """
    Uses Groq to parse the user query into a structured agent selection.
    Falls back to keyword matching if the LLM call fails.
    """
    try:
        client = get_groq_client()
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": PARSE_SYSTEM_PROMPT},
                {"role": "user",   "content": query},
            ],
            temperature=0.1,       # low temp for deterministic structured output
            max_tokens=200,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content
        return json.loads(raw)

    except Exception as e:
        logger.warning("LLM query parse failed, falling back to keywords: %s", e)
        return _keyword_fallback(query)


def _keyword_fallback(query: str) -> dict[str, Any]:
    """
    Simple keyword matching used when the LLM call fails.
    Activates an agent if any of its keywords appear in the query.
    If no keywords match, activates all agents (safe default).
    """
    query_lower = query.lower()
    matched = [
        agent for agent, keywords in DOMAIN_KEYWORDS.items()
        if any(kw in query_lower for kw in keywords)
    ]
    if not matched:
        matched = list(DISPATCHABLE_AGENTS)   # fallback: run everything

    return {
        "agents": [a.value for a in matched],
        "focus": query,
        "reasoning": "keyword match fallback",
    }


# ─────────────────────────────────────────────
# Retry logic
# ─────────────────────────────────────────────

def _select_agents_for_retry(state: VitalSyncState) -> list[AgentName]:
    """
    On a retry round, re-activates only the agents whose InsightMessage
    had confidence below the threshold.
    If all agents were confident (unlikely if we're retrying), falls back
    to re-running all agents.
    """
    weak_agents = [
        msg.agent
        for msg in state.get("insight_messages", [])
        if msg.confidence < CONFIDENCE_THRESHOLD
        and msg.agent in DISPATCHABLE_AGENTS
    ]
    return weak_agents if weak_agents else list(DISPATCHABLE_AGENTS)


def _build_retry_query(state: VitalSyncState) -> str:
    """
    Augments the original query with context from the first pass.
    Tells the retrying agents what the correlator found so far,
    and asks them to dig deeper into the weak areas.
    """
    original = state.get("query", "")
    correlation = state.get("correlation_result")
    weak_agents = _select_agents_for_retry(state)
    weak_domains = [a.value for a in weak_agents]

    if correlation:
        return (
            f"{original}\n\n"
            f"[RETRY CONTEXT] The correlator found this pattern so far: "
            f"{correlation.pattern_title}. "
            f"Please dig deeper into: {', '.join(weak_domains)}. "
            f"Look for additional supporting evidence or contradictions."
        )
    return (
        f"{original}\n\n"
        f"[RETRY CONTEXT] Initial analysis was inconclusive for: "
        f"{', '.join(weak_domains)}. Please look more carefully at the data."
    )


# ─────────────────────────────────────────────
# Main supervisor run function
# ─────────────────────────────────────────────

def run(state: VitalSyncState) -> dict:
    """
    Supervisor node entry point. Returns a partial state update.

    On round 0: parses query, selects agents, emits stream event.
    On retry:   picks weak agents, augments query, increments round.
    """
    retry_round = state.get("retry_round", 0)
    should_retry = state.get("should_retry", False)
    status_update = dict(state.get("agent_status", {}))
    stream_events: list[StreamEvent] = []

    # ── Retry round ───────────────────────────────────────────────
    if should_retry and retry_round > 0:
        logger.info("Supervisor: retry round %d", retry_round)

        selected_agents = _select_agents_for_retry(state)
        augmented_query = _build_retry_query(state)

        # Reset status for retrying agents
        for agent in selected_agents:
            status_update[agent.value] = AgentStatus.RETRYING

        stream_events.append(StreamEvent(
            event_type=StreamEventType.AGENT_START,
            agent=AgentName.SUPERVISOR,
            content=f"Retry round {retry_round}: re-running {[a.value for a in selected_agents]}",
            metadata={"retry_round": retry_round, "agents": [a.value for a in selected_agents]},
        ))

        return {
            "active_agents":  selected_agents,
            "agent_status":   status_update,
            "query":          augmented_query,
            "retry_round":    retry_round + 1,
            "should_retry":   False,           # reset — correlator will set again if needed
            "stream_events":  stream_events,
        }

    # ── First pass ────────────────────────────────────────────────
    logger.info("Supervisor: first pass, parsing query: %s", state["query"])

    parse_result = parse_query_with_llm(state["query"])

    # Convert string agent names to AgentName enum values
    raw_agents = parse_result.get("agents", [a.value for a in DISPATCHABLE_AGENTS])
    selected_agents = []
    for name in raw_agents:
        try:
            selected_agents.append(AgentName(name))
        except ValueError:
            logger.warning("Unknown agent name from LLM parse: %s", name)

    # Safety: always have at least one agent
    if not selected_agents:
        selected_agents = list(DISPATCHABLE_AGENTS)

    # Mark selected agents as IDLE (ready to be dispatched)
    for agent in selected_agents:
        status_update[agent.value] = AgentStatus.IDLE

    # Mark unselected agents as SKIPPED
    for agent in DISPATCHABLE_AGENTS:
        if agent not in selected_agents:
            status_update[agent.value] = AgentStatus.SKIPPED

    stream_events.append(StreamEvent(
        event_type=StreamEventType.AGENT_START,
        agent=AgentName.SUPERVISOR,
        content=(
            f"Activating agents: {[a.value for a in selected_agents]}. "
            f"Reason: {parse_result.get('reasoning', 'query analysis')}"
        ),
        metadata={
            "selected_agents": [a.value for a in selected_agents],
            "focus":           parse_result.get("focus", ""),
            "reasoning":       parse_result.get("reasoning", ""),
        },
    ))

    logger.info(
        "Supervisor selected agents: %s (reason: %s)",
        [a.value for a in selected_agents],
        parse_result.get("reasoning"),
    )

    return {
        "active_agents":  selected_agents,
        "agent_status":   status_update,
        "retry_round":    0,
        "should_retry":   False,
        "stream_events":  stream_events,
    }