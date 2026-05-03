"""
orchestrator/graph.py
─────────────────────
Builds and compiles the VitalSync StateGraph.

Graph topology
──────────────

                        ┌─────────────┐
                        │  supervisor │  ← entry point
                        └──────┬──────┘
                               │ Send() fan-out (parallel)
          ┌──────────┬─────────┼──────────┬──────────┐
          ▼          ▼         ▼          ▼          ▼
       [sleep]  [activity] [nutrition] [stress]  [weather]
          └──────────┴─────────┼──────────┴──────────┘
                               │ all write InsightMessages
                               ▼
                          [correlator]
                               │
                               ▼
                    ┌─────────────────────┐
                    │ confidence ≥ 0.70?  │
                    └──────┬──────────────┘
                    yes ◄──┘   └──► no (& round < MAX)
                    │                    │
                    ▼                    ▼
                 [coach]           [supervisor]  ← retry loop
                    │              (partial re-run)
                    ▼
                  END

Key LangGraph patterns used
────────────────────────────
1. Send() API — supervisor dispatches to multiple domain agent nodes
   simultaneously. LangGraph runs them in parallel threads and waits
   for all to complete before moving to the correlator.

2. Conditional edges — after the correlator writes confidence_score,
   `route_after_correlator` decides whether to proceed to the coach
   or loop back to the supervisor for a retry round.

3. Append-only state — insight_messages uses operator.add so parallel
   agents can all write without conflicts. LangGraph handles the merge.
"""

from __future__ import annotations

from langgraph.graph import StateGraph, END
from langgraph.constants import Send

from .state import (
    VitalSyncState,
    AgentName,
    AgentStatus,
    CONFIDENCE_THRESHOLD,
    MAX_RETRY_ROUNDS,
)

# Agent node functions are imported lazily to keep this file readable.
# Each returns a partial VitalSyncState update dict.
try:
    from ..agents.sleep_agent     import run as sleep_run
    from ..agents.activity_agent  import run as activity_run
    from ..agents.nutrition_agent import run as nutrition_run
    from ..agents.stress_agent    import run as stress_run
    from ..agents.weather_agent   import run as weather_run
    from ..agents.correlator_agent import run as correlator_run
    from ..agents.coach_agent     import run as coach_run
    from .supervisor import run as supervisor_run
except Exception:
    from backend.agents.sleep_agent     import run as sleep_run
    from backend.agents.activity_agent  import run as activity_run
    from backend.agents.nutrition_agent import run as nutrition_run
    from backend.agents.stress_agent    import run as stress_run
    from backend.agents.weather_agent   import run as weather_run
    from backend.agents.correlator_agent import run as correlator_run
    from backend.agents.coach_agent     import run as coach_run
    from backend.orchestrator.supervisor import run as supervisor_run


# ─────────────────────────────────────────────
# Routing functions
# ─────────────────────────────────────────────

def route_after_supervisor(state: VitalSyncState) -> list[Send]:
    """
    Called after the supervisor node completes.

    Returns a list of Send() objects — one per active agent.
    LangGraph executes all of them in parallel, collects their
    partial state updates, and merges them before continuing.

    Each Send() carries a copy of the current state so agents
    have full context (the query, session_id, retry_round, etc.)
    """
    sends = []
    for agent_name in state["active_agents"]:
        node_name = f"agent_{agent_name.value}"
        sends.append(Send(node_name, state))
    return sends


def route_after_correlator(state: VitalSyncState) -> str:
    """
    Called after the correlator node completes.

    Decision logic:
      - confidence ≥ threshold → move to coach (done)
      - confidence < threshold AND retries remaining → loop back to supervisor
      - confidence < threshold AND retries exhausted → move to coach anyway
        (coach will note low confidence in its response)
    """
    score = state.get("confidence_score", 0.0)
    retry_round = state.get("retry_round", 0)

    if score >= CONFIDENCE_THRESHOLD:
        return "coach"

    if retry_round < MAX_RETRY_ROUNDS:
        return "supervisor"   # supervisor will set should_retry=True, pick weak agents

    # exhausted retries — proceed with what we have
    return "coach"


# ─────────────────────────────────────────────
# Wrapper nodes
# ─────────────────────────────────────────────
# LangGraph nodes must be plain callables: (state) -> partial_state_dict.
# We wrap each agent's `run` function to ensure consistent return typing
# and to update agent_status before and after execution.

def _make_domain_node(agent_name: AgentName, run_fn):
    """
    Factory that creates a domain agent node with status bookkeeping.
    Sets status to RUNNING at start, DONE at completion.
    """
    def node(state: VitalSyncState) -> dict:
        # Mark this agent as running
        status_update = dict(state.get("agent_status", {}))
        status_update[agent_name.value] = AgentStatus.RUNNING

        # Run the agent — returns partial state (insight_messages, stream_events)
        result = run_fn(state)

        # Mark as done
        status_update[agent_name.value] = AgentStatus.DONE
        result["agent_status"] = status_update
        return result

    node.__name__ = f"agent_{agent_name.value}"
    return node


def supervisor_node(state: VitalSyncState) -> dict:
    """
    Entry point and retry handler.
    First call: parses query, selects all relevant agents.
    Retry call: state['should_retry'] is True, supervisor picks only
                the agents whose InsightMessage had low confidence.
    """
    return supervisor_run(state)


def correlator_node(state: VitalSyncState) -> dict:
    """Reads all InsightMessages, finds cross-domain patterns."""
    return correlator_run(state)


def coach_node(state: VitalSyncState) -> dict:
    """Turns the correlation result into the final user-facing response."""
    return coach_run(state)


# Domain agent nodes (one per agent, created by factory)
sleep_node      = _make_domain_node(AgentName.SLEEP,     sleep_run)
activity_node   = _make_domain_node(AgentName.ACTIVITY,  activity_run)
nutrition_node  = _make_domain_node(AgentName.NUTRITION, nutrition_run)
stress_node     = _make_domain_node(AgentName.STRESS,    stress_run)
weather_node    = _make_domain_node(AgentName.WEATHER,   weather_run)


# ─────────────────────────────────────────────
# Graph construction
# ─────────────────────────────────────────────

def build_graph() -> StateGraph:
    """
    Assembles and returns the compiled VitalSync StateGraph.
    Called once at application startup; the compiled graph is reused
    for every query (it is stateless — state is passed in per-invoke).
    """
    builder = StateGraph(VitalSyncState)

    # ── Register nodes ────────────────────────────────────────────
    builder.add_node("supervisor",          supervisor_node)
    builder.add_node("agent_sleep",         sleep_node)
    builder.add_node("agent_activity",      activity_node)
    builder.add_node("agent_nutrition",     nutrition_node)
    builder.add_node("agent_stress",        stress_node)
    builder.add_node("agent_weather",       weather_node)
    builder.add_node("correlator",          correlator_node)
    builder.add_node("coach",               coach_node)

    # ── Entry point ───────────────────────────────────────────────
    builder.set_entry_point("supervisor")

    # ── Supervisor → parallel domain agents (Send() fan-out) ──────
    # route_after_supervisor returns a list of Send() objects.
    # LangGraph runs them all in parallel and joins before correlator.
    builder.add_conditional_edges(
        "supervisor",
        route_after_supervisor,
        # Tell LangGraph which node names are valid Send() targets
        [
            "agent_sleep",
            "agent_activity",
            "agent_nutrition",
            "agent_stress",
            "agent_weather",
        ],
    )

    # ── All domain agents → correlator ────────────────────────────
    # Each domain agent node has a direct edge to correlator.
    # LangGraph's parallel join waits for all active agents before
    # advancing to correlator (this is automatic with Send() fan-out).
    for node_name in [
        "agent_sleep",
        "agent_activity",
        "agent_nutrition",
        "agent_stress",
        "agent_weather",
    ]:
        builder.add_edge(node_name, "correlator")

    # ── Correlator → coach or supervisor (retry) ──────────────────
    builder.add_conditional_edges(
        "correlator",
        route_after_correlator,
        {
            "coach":        "coach",
            "supervisor":   "supervisor",   # retry loop
        },
    )

    # ── Coach → END ───────────────────────────────────────────────
    builder.add_edge("coach", END)

    return builder.compile()


# ─────────────────────────────────────────────
# Compiled graph singleton
# ─────────────────────────────────────────────

# Compiled once at import time. FastAPI imports this module at startup.
vitalsync_graph = build_graph()