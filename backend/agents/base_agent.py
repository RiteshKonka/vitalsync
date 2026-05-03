"""
agents/base_agent.py
────────────────────
BaseAgent provides everything a domain agent needs:
  - Groq LLM access via stream_agent_response / complete
  - MCP tool calling (calls the MCP server's tools)
  - StreamEvent emission helpers (appended to state)
  - InsightMessage construction and confidence scoring
  - Standard run() signature that graph.py expects

Domain agents subclass BaseAgent and implement:
  - AGENT_NAME: AgentName enum value
  - DOMAIN: str ("sleep", "activity", etc.)
  - SYSTEM_PROMPT: str — the agent's persona and instructions
  - _analyze(state) -> dict  — core analysis logic, returns raw findings

The base run() method wraps _analyze() with:
  1. Pre-analysis stream event (agent_start)
  2. MCP tool calls to fetch domain data
  3. LLM reasoning over the data
  4. Confidence scoring
  5. InsightMessage construction
  6. Post-analysis stream event (agent_done)
"""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from typing import Any

try:
    from ..orchestrator.state import (
        VitalSyncState,
        AgentName,
        InsightMessage,
        StreamEvent,
        StreamEventType,
    )
except Exception:
    from backend.orchestrator.state import (
        VitalSyncState,
        AgentName,
        InsightMessage,
        StreamEvent,
        StreamEventType,
    )

try:
    from ..utils.groq_client import complete
except Exception:
    try:
        from backend.utils.groq_client import complete
    except Exception:
        from utils.groq_client import complete

try:
    from ..mock_data.generator import get_data, get_weekly_pattern, get_domain_summary
except Exception:
    try:
        from backend.mock_data.generator import get_data, get_weekly_pattern, get_domain_summary
    except Exception:
        from mock_data.generator import get_data, get_weekly_pattern, get_domain_summary

logger = logging.getLogger(__name__)


class BaseAgent(ABC):

    AGENT_NAME:    AgentName
    DOMAIN:        str
    SYSTEM_PROMPT: str

    # ── MCP tool simulation ───────────────────────────────────────
    # In the full stack these call the real MCP server over stdio.
    # For now they call the mock data generator directly so the
    # agent logic works end-to-end without the MCP server running.
    # Swapping to real MCP: replace _call_tool with mcp_client calls.

    def _call_tool(self, tool_name: str, **kwargs) -> Any:
        """
        Simulates an MCP tool call.
        Emits a TOOL_CALL stream event and returns the tool result.
        In production this becomes: await mcp_client.call_tool(tool_name, kwargs)
        """
        logger.debug("[%s] tool call: %s(%s)", self.AGENT_NAME.value, tool_name, kwargs)

        # Route to mock data functions
        if tool_name == "get_domain_data":
            return get_data(kwargs.get("domain", self.DOMAIN))
        elif tool_name == "get_weekly_pattern":
            return get_weekly_pattern(
                kwargs.get("domain", self.DOMAIN),
                kwargs.get("metric", "")
            )
        elif tool_name == "get_domain_summary":
            return get_domain_summary(kwargs.get("domain", self.DOMAIN))
        else:
            raise ValueError(f"Unknown MCP tool: {tool_name}")

    # ── Data fetching helpers ─────────────────────────────────────

    def fetch_domain_data(self) -> list[dict]:
        """Fetches all 90 days of raw domain data via MCP tool."""
        return self._call_tool("get_domain_data", domain=self.DOMAIN)

    def fetch_weekly_pattern(self, metric: str) -> dict[str, float]:
        """Returns day-of-week averages for a specific metric."""
        return self._call_tool("get_weekly_pattern", domain=self.DOMAIN, metric=metric)

    def fetch_summary(self) -> dict:
        """Returns aggregate stats for the domain."""
        return self._call_tool("get_domain_summary", domain=self.DOMAIN)

    # ── LLM reasoning ─────────────────────────────────────────────

    def reason(
        self,
        user_message: str,
        data_context: str,
        temperature: float = 0.3,
    ) -> str:
        """
        Runs a single non-streaming LLM call for structured reasoning.
        Returns the full response string.
        """
        messages = [
            {
                "role": "user",
                "content": f"DATA:\n{data_context}\n\nQUESTION:\n{user_message}",
            }
        ]
        return complete(
            messages=messages,
            system=self.SYSTEM_PROMPT,
            temperature=temperature,
            max_tokens=800,
        )

    def reason_json(self, user_message: str, data_context: str) -> dict:
        """
        LLM call that returns structured JSON.
        Used for final InsightMessage construction.
        """
        messages = [
            {
                "role": "user",
                "content": (
                    f"DATA:\n{data_context}\n\n"
                    f"QUESTION:\n{user_message}\n\n"
                    f"Return ONLY valid JSON, no prose, no markdown fences."
                ),
            }
        ]
        raw = complete(
            messages=messages,
            system=self.SYSTEM_PROMPT + "\n\nYou MUST respond with valid JSON only.",
            temperature=0.1,
            max_tokens=800,
            json_mode=True,
        )
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("[%s] JSON parse failed, returning empty dict", self.AGENT_NAME.value)
            return {}

    # ── Stream event helpers ──────────────────────────────────────

    def _start_event(self, message: str = "") -> StreamEvent:
        return StreamEvent(
            event_type=StreamEventType.AGENT_START,
            agent=self.AGENT_NAME,
            content=message or f"{self.AGENT_NAME.value} agent starting analysis",
        )

    def _thought_event(self, chunk: str) -> StreamEvent:
        return StreamEvent(
            event_type=StreamEventType.AGENT_THOUGHT,
            agent=self.AGENT_NAME,
            content=chunk,
        )

    def _tool_event(self, tool_name: str, result_summary: str) -> StreamEvent:
        return StreamEvent(
            event_type=StreamEventType.TOOL_CALL,
            agent=self.AGENT_NAME,
            content=f"Called {tool_name}",
            metadata={"result_summary": result_summary},
        )

    def _a2a_event(self, insight: InsightMessage) -> StreamEvent:
        return StreamEvent(
            event_type=StreamEventType.A2A_MESSAGE,
            agent=self.AGENT_NAME,
            content=insight.summary,
            metadata={
                "confidence":   insight.confidence,
                "anomalies":    insight.anomalies,
                "key_metrics":  insight.key_metrics,
            },
        )

    def _done_event(self, confidence: float) -> StreamEvent:
        return StreamEvent(
            event_type=StreamEventType.AGENT_DONE,
            agent=self.AGENT_NAME,
            content=f"Analysis complete (confidence: {confidence:.0%})",
            metadata={"confidence": confidence},
        )

    # ── InsightMessage builder ────────────────────────────────────

    def _build_insight(
        self,
        summary:      str,
        key_metrics:  dict[str, Any],
        anomalies:    list[str],
        data_points:  list[dict],
        confidence:   float,
        retry_round:  int = 0,
    ) -> InsightMessage:
        return InsightMessage(
            agent=self.AGENT_NAME,
            domain=self.DOMAIN,
            summary=summary,
            key_metrics=key_metrics,
            anomalies=anomalies,
            data_points=data_points[:10],  # cap to 10 rows to keep state lean
            confidence=min(1.0, max(0.0, confidence)),
            retry_round=retry_round,
        )

    # ── Abstract interface ────────────────────────────────────────

    @abstractmethod
    def _analyze(self, state: VitalSyncState) -> dict[str, Any]:
        """
        Core analysis logic. Subclasses implement this.
        Must return a dict with keys:
          summary:     str
          key_metrics: dict
          anomalies:   list[str]
          data_points: list[dict]
          confidence:  float
        """
        ...

    # ── Main entry point ──────────────────────────────────────────

    def run(self, state: VitalSyncState) -> dict:
        """
        Called by the LangGraph node wrapper in graph.py.
        Returns a partial state update dict.
        """
        stream_events: list[StreamEvent] = [self._start_event()]
        retry_round = state.get("retry_round", 0)

        try:
            findings = self._analyze(state)

            insight = self._build_insight(
                summary=findings.get("summary", "No findings."),
                key_metrics=findings.get("key_metrics", {}),
                anomalies=findings.get("anomalies", []),
                data_points=findings.get("data_points", []),
                confidence=findings.get("confidence", 0.5),
                retry_round=retry_round,
            )

            stream_events.append(self._a2a_event(insight))
            stream_events.append(self._done_event(insight.confidence))

            logger.info(
                "[%s] done — confidence %.2f — anomalies: %s",
                self.AGENT_NAME.value,
                insight.confidence,
                insight.anomalies,
            )

            return {
                "insight_messages": [insight],
                "stream_events":    stream_events,
            }

        except Exception as e:
            logger.error("[%s] analysis failed: %s", self.AGENT_NAME.value, e, exc_info=True)
            error_event = StreamEvent(
                event_type=StreamEventType.ERROR,
                agent=self.AGENT_NAME,
                content=f"Agent failed: {e}",
            )
            # Return a low-confidence insight so the graph can continue
            fallback = self._build_insight(
                summary=f"Analysis failed: {e}",
                key_metrics={},
                anomalies=[],
                data_points=[],
                confidence=0.1,
                retry_round=retry_round,
            )
            return {
                "insight_messages": [fallback],
                "stream_events":    stream_events + [error_event],
            }