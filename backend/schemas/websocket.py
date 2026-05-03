"""
schemas/websocket.py
────────────────────
Typed models for every WebSocket frame exchanged between
the FastAPI backend and the React frontend.

Client → Server frames:
  QueryFrame      — user submits a question

Server → Client frames:
  ProcessingFrame  — "activating agents..."
  AgentStartFrame  — agent begins work
  AgentThoughtFrame — streaming token from agent
  AgentDoneFrame   — agent finished
  ToolCallFrame    — agent called an MCP tool
  A2AMessageFrame  — agent posted an InsightMessage (A2A event)
  CorrelationFrame — correlator found a pattern
  FinalAnswerFrame — coach produced the final response
  DoneFrame        — full run complete
  ErrorFrame       — something went wrong

These models are used by:
  1. api/websocket.py  — to construct outbound frames
  2. frontend/src/types/agents.ts  — TypeScript mirrors of these shapes
     (manually kept in sync, or auto-generated via openapi-ts)
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional, Union
from pydantic import BaseModel, Field


# ── Client → Server ───────────────────────────────────────────────

class QueryFrame(BaseModel):
    """Sent by the React frontend when the user submits a query."""
    type:       Literal["query"] = "query"
    session_id: str
    query:      str = Field(min_length=1, max_length=500)


# ── Server → Client ───────────────────────────────────────────────

class ProcessingFrame(BaseModel):
    type:    Literal["processing"] = "processing"
    content: str = "Activating agents..."


class AgentStartFrame(BaseModel):
    type:      Literal["agent_start"] = "agent_start"
    agent:     str
    content:   str
    metadata:  dict[str, Any] = {}
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class AgentThoughtFrame(BaseModel):
    """Streaming token chunk from an agent's LLM call."""
    type:      Literal["agent_thought"] = "agent_thought"
    agent:     str
    content:   str   # one token or small chunk
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class AgentDoneFrame(BaseModel):
    type:       Literal["agent_done"] = "agent_done"
    agent:      str
    content:    str
    metadata:   dict[str, Any] = {}   # includes confidence score
    timestamp:  datetime = Field(default_factory=datetime.utcnow)


class ToolCallFrame(BaseModel):
    """Agent called an MCP tool."""
    type:      Literal["tool_call"] = "tool_call"
    agent:     str
    content:   str   # "Called get_sleep_data"
    metadata:  dict[str, Any] = {}   # result_summary
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class A2AMessageFrame(BaseModel):
    """
    Agent posted an InsightMessage to the shared A2A bus.
    This is the key multi-agent event — lets the frontend show
    each agent's contribution as it arrives.
    """
    type:      Literal["a2a_message"] = "a2a_message"
    agent:     str
    content:   str    # the insight summary
    metadata:  dict[str, Any] = {}   # confidence, anomalies, key_metrics
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class CorrelationFrame(BaseModel):
    """
    Correlator found a cross-domain pattern.
    Metadata includes causal_chain, involved_domains, confidence.
    """
    type:      Literal["correlation"] = "correlation"
    agent:     Literal["correlator"] = "correlator"
    content:   str    # pattern_title
    metadata:  dict[str, Any] = {}
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class FinalAnswerFrame(BaseModel):
    """
    Coach produced the final response.
    Metadata contains explanation, action_items, domains_cited.
    """
    type:      Literal["final_answer"] = "final_answer"
    agent:     Literal["coach"] = "coach"
    content:   str    # headline
    metadata:  dict[str, Any] = {}
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class DoneFrame(BaseModel):
    """Signals the end of a full query run."""
    type:       Literal["done"] = "done"
    session_id: str


class ErrorFrame(BaseModel):
    """Something went wrong — frontend should show an error state."""
    type:    Literal["error"] = "error"
    message: str
    agent:   Optional[str] = None


# ── Union type for type-safe deserialization on the frontend ──────

ServerFrame = Union[
    ProcessingFrame,
    AgentStartFrame,
    AgentThoughtFrame,
    AgentDoneFrame,
    ToolCallFrame,
    A2AMessageFrame,
    CorrelationFrame,
    FinalAnswerFrame,
    DoneFrame,
    ErrorFrame,
]


# ── Frame builder helpers (used by api/websocket.py) ─────────────

def make_frame(event) -> dict[str, Any]:
    """
    Converts a StreamEvent (from orchestrator/state.py) into a
    plain dict ready to be JSON-serialised and sent over the WebSocket.
    """
    return {
        "type":      event.event_type.value,
        "agent":     event.agent.value,
        "content":   event.content,
        "metadata":  event.metadata,
        "timestamp": event.timestamp.isoformat(),
    }


def make_error_frame(message: str, agent: str | None = None) -> dict[str, Any]:
    return {"type": "error", "message": message, "agent": agent}


def make_done_frame(session_id: str) -> dict[str, Any]:
    return {"type": "done", "session_id": session_id}


def make_processing_frame(content: str = "Activating agents...") -> dict[str, Any]:
    return {"type": "processing", "content": content}