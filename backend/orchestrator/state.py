"""
orchestrator/state.py
─────────────────────
The single source of truth that flows through the entire LangGraph graph.
Every agent node receives this state, reads what it needs, and returns
a partial update. LangGraph merges all partial updates automatically.

Key design decisions:
  - InsightMessage is the A2A communication primitive. Domain agents write
    one each; the correlator reads all of them.
  - `agent_status` lets the supervisor and the frontend know exactly which
    agents are running, done, or skipped at any moment.
  - `stream_events` is an append-only log of tokens/thoughts that the
    FastAPI WebSocket handler drains and pushes to the React frontend.
  - `confidence_score` drives the retry loop: if the correlator scores its
    own synthesis below CONFIDENCE_THRESHOLD, the supervisor sends the
    weakest agents back for a clarification round.
"""

from __future__ import annotations

import operator
from datetime import datetime
from enum import Enum
from typing import Annotated, Any, Optional
from pydantic import BaseModel, Field
from typing_extensions import TypedDict


# ─────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────

CONFIDENCE_THRESHOLD = 0.70   # below this → supervisor triggers retry
MAX_RETRY_ROUNDS = 2           # hard cap on clarification rounds


# ─────────────────────────────────────────────
# Enums
# ─────────────────────────────────────────────

class AgentName(str, Enum):
    SUPERVISOR   = "supervisor"
    SLEEP        = "sleep"
    ACTIVITY     = "activity"
    NUTRITION    = "nutrition"
    STRESS       = "stress"
    WEATHER      = "weather"
    CORRELATOR   = "correlator"
    COACH        = "coach"


class AgentStatus(str, Enum):
    IDLE      = "idle"       # not yet activated this run
    RUNNING   = "running"    # currently executing
    DONE      = "done"       # finished, insight written
    SKIPPED   = "skipped"    # supervisor decided not to activate
    RETRYING  = "retrying"   # sent back for clarification round


class StreamEventType(str, Enum):
    AGENT_START    = "agent_start"     # agent begins thinking
    AGENT_THOUGHT  = "agent_thought"   # token chunk from agent
    AGENT_DONE     = "agent_done"      # agent finished
    TOOL_CALL      = "tool_call"       # agent called an MCP tool
    TOOL_RESULT    = "tool_result"     # MCP tool returned data
    A2A_MESSAGE    = "a2a_message"     # agent posted an InsightMessage
    CORRELATION    = "correlation"     # correlator found a pattern
    FINAL_ANSWER   = "final_answer"    # coach response ready
    ERROR          = "error"           # something went wrong


# ─────────────────────────────────────────────
# A2A communication primitive
# ─────────────────────────────────────────────

class InsightMessage(BaseModel):
    """
    The message every domain agent writes into shared state.
    The correlator reads all of these — this is the A2A protocol.

    `confidence` is the agent's own estimate of how reliable its
    finding is (0.0–1.0). Low confidence triggers a retry from supervisor.
    `data_points` are the raw evidence snippets the correlator can cite.
    """
    agent:          AgentName
    domain:         str                        # "sleep", "activity", etc.
    summary:        str                        # 1–2 sentence finding
    key_metrics:    dict[str, Any]             # structured metrics found
    anomalies:      list[str]                  # notable deviations from baseline
    data_points:    list[dict[str, Any]]       # raw evidence rows
    confidence:     float = Field(ge=0.0, le=1.0)
    timestamp:      datetime = Field(default_factory=datetime.utcnow)
    retry_round:    int = 0                    # which clarification round


class CorrelationResult(BaseModel):
    """
    Written by the correlator agent after reading all InsightMessages.
    Contains the cross-domain causal chain it found.
    """
    pattern_title:      str                        # short name, e.g. "Tuesday fatigue loop"
    causal_chain:       list[str]                  # ordered list of cause → effect steps
    involved_domains:   list[AgentName]
    supporting_metrics: dict[str, Any]             # evidence from each domain
    confidence:         float = Field(ge=0.0, le=1.0)
    alternative_hypotheses: list[str] = []         # other possible explanations


class CoachResponse(BaseModel):
    """
    Final output written by the coach agent. This is what the user sees.
    """
    headline:       str                            # one-sentence answer
    explanation:    str                            # full explanation paragraph
    action_items:   list[str]                      # concrete things to try
    domains_cited:  list[AgentName]
    correlation:    Optional[CorrelationResult] = None


# ─────────────────────────────────────────────
# Stream event (frontend protocol)
# ─────────────────────────────────────────────

class StreamEvent(BaseModel):
    """
    Emitted by agents as they work. FastAPI WebSocket handler picks these
    up from state['stream_events'] and pushes them to the React frontend.
    """
    event_type:  StreamEventType
    agent:       AgentName
    content:     str = ""                          # token chunk or message
    metadata:    dict[str, Any] = {}
    timestamp:   datetime = Field(default_factory=datetime.utcnow)


# ─────────────────────────────────────────────
# Main graph state
# ─────────────────────────────────────────────

class VitalSyncState(TypedDict):
    """
    The complete state object passed between every node in the LangGraph graph.

    LangGraph merges partial updates returned by each node.
    Lists marked with Annotated[list, operator.add] are append-only —
    agents can only add to them, never overwrite. This prevents race
    conditions when multiple agents complete simultaneously.
    """

    # ── Query context ──────────────────────────────────────────────
    query:              str                        # user's current question
    session_id:         str                        # ties requests to health data
    retry_round:        int                        # current clarification round (0 = first pass)

    # ── Agent coordination ─────────────────────────────────────────
    active_agents:      list[AgentName]            # agents supervisor decided to run
    agent_status:       dict[str, AgentStatus]     # live status per agent name

    # ── A2A message bus (append-only) ─────────────────────────────
    # operator.add means LangGraph merges these by concatenation,
    # not by replacement. Multiple agents can write safely in parallel.
    insight_messages:   Annotated[list[InsightMessage], operator.add]

    # ── Synthesis layer ────────────────────────────────────────────
    correlation_result: Optional[CorrelationResult]
    confidence_score:   float                      # set by correlator, checked by supervisor
    coach_response:     Optional[CoachResponse]

    # ── Conversation history (append-only) ────────────────────────
    messages:           Annotated[list[dict[str, str]], operator.add]

    # ── Frontend stream (append-only) ─────────────────────────────
    stream_events:      Annotated[list[StreamEvent], operator.add]

    # ── Control flags ──────────────────────────────────────────────
    should_retry:       bool                       # supervisor sets True to trigger retry
    is_complete:        bool                       # supervisor sets True to end graph


# ─────────────────────────────────────────────
# State factory
# ─────────────────────────────────────────────

def initial_state(query: str, session_id: str) -> VitalSyncState:
    """
    Returns a clean initial state for a new query run.
    Called by the FastAPI route handler before invoking the graph.
    """
    return VitalSyncState(
        query=query,
        session_id=session_id,
        retry_round=0,
        active_agents=[],
        agent_status={agent.value: AgentStatus.IDLE for agent in AgentName},
        insight_messages=[],
        correlation_result=None,
        confidence_score=0.0,
        coach_response=None,
        messages=[{"role": "user", "content": query}],
        stream_events=[],
        should_retry=False,
        is_complete=False,
    )