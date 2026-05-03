"""
schemas/insight.py
──────────────────
API-layer Pydantic models for insights, correlations, and coach responses.

These are the serialisable counterparts to the dataclasses in
orchestrator/state.py — they are safe to return from FastAPI endpoints
and safe to send over the WebSocket as JSON.

Relationship to state.py:
  state.py   → InsightMessage, CorrelationResult, CoachResponse (internal graph types)
  schemas/insight.py → same shapes, but with .model_dump() / JSON serialisation
                       and without circular imports from orchestrator.

Used by:
  - /api/session/{id} to return past insights
  - WebSocket final_answer frame metadata
  - Frontend TypeScript type generation
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field


# ── Enums (mirrors orchestrator/state.py — no import dependency) ──

class AgentNameSchema(str, Enum):
    SUPERVISOR  = "supervisor"
    SLEEP       = "sleep"
    ACTIVITY    = "activity"
    NUTRITION   = "nutrition"
    STRESS      = "stress"
    WEATHER     = "weather"
    CORRELATOR  = "correlator"
    COACH       = "coach"


class StreamEventTypeSchema(str, Enum):
    AGENT_START    = "agent_start"
    AGENT_THOUGHT  = "agent_thought"
    AGENT_DONE     = "agent_done"
    TOOL_CALL      = "tool_call"
    TOOL_RESULT    = "tool_result"
    A2A_MESSAGE    = "a2a_message"
    CORRELATION    = "correlation"
    FINAL_ANSWER   = "final_answer"
    PROCESSING     = "processing"
    DONE           = "done"
    ERROR          = "error"


# ── A2A message (what domain agents write) ────────────────────────

class InsightMessageSchema(BaseModel):
    """
    Serialisable version of orchestrator/state.InsightMessage.
    Written by each domain agent, read by the correlator.
    """
    agent:        AgentNameSchema
    domain:       str
    summary:      str
    key_metrics:  dict[str, Any]
    anomalies:    list[str]
    data_points:  list[dict[str, Any]]
    confidence:   float = Field(ge=0.0, le=1.0)
    timestamp:    datetime
    retry_round:  int = 0

    model_config = {"from_attributes": True}


# ── Correlation result (what the correlator writes) ───────────────

class CorrelationResultSchema(BaseModel):
    """
    Serialisable version of orchestrator/state.CorrelationResult.
    The cross-domain causal chain found by the correlator.
    """
    pattern_title:          str
    causal_chain:           list[str]
    involved_domains:       list[AgentNameSchema]
    supporting_metrics:     dict[str, Any]
    confidence:             float = Field(ge=0.0, le=1.0)
    alternative_hypotheses: list[str] = []

    model_config = {"from_attributes": True}


# ── Coach response (what the user sees) ──────────────────────────

class CoachResponseSchema(BaseModel):
    """
    Serialisable version of orchestrator/state.CoachResponse.
    Returned in the WebSocket final_answer frame and saved to session history.
    """
    headline:      str
    explanation:   str
    action_items:  list[str]
    domains_cited: list[AgentNameSchema]
    correlation:   Optional[CorrelationResultSchema] = None

    model_config = {"from_attributes": True}


# ── WebSocket stream event ────────────────────────────────────────

class StreamEventSchema(BaseModel):
    """
    A single frame sent over the WebSocket from server to client.
    The 'type' field drives which React component renders it.
    """
    type:       StreamEventTypeSchema
    agent:      AgentNameSchema
    content:    str = ""
    metadata:   dict[str, Any] = {}
    timestamp:  datetime

    model_config = {"from_attributes": True}


# ── Session history entry ─────────────────────────────────────────

class QueryHistoryEntry(BaseModel):
    """One past query + response stored in a Session."""
    query:     str
    timestamp: float
    response:  CoachResponseSchema


class SessionHistorySchema(BaseModel):
    session_id: str
    history:    list[QueryHistoryEntry]
    count:      int


# ── Conversion helpers ────────────────────────────────────────────

def insight_to_schema(msg) -> InsightMessageSchema:
    """Convert orchestrator InsightMessage → InsightMessageSchema."""
    return InsightMessageSchema(
        agent=AgentNameSchema(msg.agent.value),
        domain=msg.domain,
        summary=msg.summary,
        key_metrics=msg.key_metrics,
        anomalies=msg.anomalies,
        data_points=msg.data_points,
        confidence=msg.confidence,
        timestamp=msg.timestamp,
        retry_round=msg.retry_round,
    )


def correlation_to_schema(result) -> CorrelationResultSchema:
    """Convert orchestrator CorrelationResult → CorrelationResultSchema."""
    return CorrelationResultSchema(
        pattern_title=result.pattern_title,
        causal_chain=result.causal_chain,
        involved_domains=[AgentNameSchema(d.value) for d in result.involved_domains],
        supporting_metrics=result.supporting_metrics,
        confidence=result.confidence,
        alternative_hypotheses=result.alternative_hypotheses,
    )


def coach_to_schema(response) -> CoachResponseSchema:
    """Convert orchestrator CoachResponse → CoachResponseSchema."""
    return CoachResponseSchema(
        headline=response.headline,
        explanation=response.explanation,
        action_items=response.action_items,
        domains_cited=[AgentNameSchema(a.value) for a in response.domains_cited],
        correlation=(
            correlation_to_schema(response.correlation)
            if response.correlation else None
        ),
    )