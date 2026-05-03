"""
agents/coach_agent.py
─────────────────────
The coach is the final voice the user hears.

It receives the CorrelationResult from the correlator and translates
the multi-domain causal chain into a clear, empathetic, actionable response.

It does NOT re-analyze data. Its only job is communication:
  - Explain *why* the pattern exists in plain English
  - Give specific, prioritised action items
  - Acknowledge if confidence was low
  - Never overwhelm the user with jargon
"""

from __future__ import annotations
import logging
from typing import Any

from ..orchestrator.state import (
    VitalSyncState,
    AgentName,
    CoachResponse,
    StreamEvent,
    StreamEventType,
    CONFIDENCE_THRESHOLD,
)
from ..utils.groq_client import complete

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are the Health Coach Agent for VitalSync — the final voice the user hears.

You receive a correlation result from a multi-agent analysis system and your job is to:
1. Explain the finding clearly and warmly — no jargon, no walls of text.
2. Give 3–5 specific, actionable steps the user can try starting today.
3. Acknowledge uncertainty honestly if confidence was below 70%.
4. Keep the headline to ONE clear sentence that directly answers the user's question.
5. Keep the explanation to 3–4 sentences.

Tone: like a knowledgeable friend, not a doctor or a textbook.
Never start with "I" or with sycophantic openers.
Be direct. The user wants to know what to DO.

Return ONLY valid JSON:
{
  "headline": "One direct sentence answering the user's question",
  "explanation": "3-4 sentence explanation of the pattern",
  "action_items": [
    "Specific action 1",
    "Specific action 2",
    "Specific action 3"
  ],
  "domains_cited": ["sleep", "activity", "nutrition", "stress"]
}"""


def run(state: VitalSyncState) -> dict:
    """
    Coach node. Reads correlation_result, writes coach_response.
    """
    stream_events: list[StreamEvent] = []
    correlation  = state.get("correlation_result")
    query        = state.get("query", "")
    confidence   = state.get("confidence_score", 0.5)

    stream_events.append(StreamEvent(
        event_type=StreamEventType.AGENT_START,
        agent=AgentName.COACH,
        content="Preparing your personalised health insight...",
    ))

    if not correlation:
        logger.warning("Coach: no correlation result available")
        coach_resp = CoachResponse(
            headline="Not enough data to find a clear pattern yet.",
            explanation="The analysis didn't find a strong enough signal. Try asking a more specific question.",
            action_items=["Keep tracking consistently for more data."],
            domains_cited=[],
        )
        return _finish(coach_resp, stream_events, state)

    import json
    correlation_context = f"""
Pattern found: {correlation.pattern_title}
Confidence: {confidence:.0%}

Causal chain:
{json.dumps(correlation.causal_chain, indent=2)}

Supporting evidence:
{json.dumps(correlation.supporting_metrics, indent=2)}

Alternative hypotheses:
{json.dumps(correlation.alternative_hypotheses, indent=2)}
"""
    low_confidence_note = ""
    if confidence < CONFIDENCE_THRESHOLD:
        low_confidence_note = (
            "\n\nNote: confidence is below 70%. "
            "Acknowledge the uncertainty and suggest the user watch for the pattern."
        )

    prompt = f"""
The user asked: "{query}"

Here is what the multi-agent analysis found:

{correlation_context}
{low_confidence_note}

Write a coaching response. Return JSON only.
"""

    raw = complete(
        messages=[{"role": "user", "content": prompt}],
        system=SYSTEM_PROMPT,
        temperature=0.4,
        max_tokens=600,
        json_mode=True,
    )

    try:
        data = json.loads(raw)
    except Exception:
        data = {}

    if data.get("headline"):
        involved_agents = []
        for d in data.get("domains_cited", []):
            try:
                involved_agents.append(AgentName(d))
            except ValueError:
                pass

        coach_resp = CoachResponse(
            headline=data["headline"],
            explanation=data.get("explanation", ""),
            action_items=data.get("action_items", []),
            domains_cited=involved_agents,
            correlation=correlation,
        )
    else:
        coach_resp = _build_fallback_response(correlation, confidence)

    return _finish(coach_resp, stream_events, state)


def _finish(coach_resp: CoachResponse, stream_events: list, state: VitalSyncState) -> dict:
    import json
    stream_events.append(StreamEvent(
        event_type=StreamEventType.FINAL_ANSWER,
        agent=AgentName.COACH,
        content=coach_resp.headline,
        metadata={
            "explanation":   coach_resp.explanation,
            "action_items":  coach_resp.action_items,
            "domains_cited": [a.value for a in coach_resp.domains_cited],
        },
    ))
    return {
        "coach_response": coach_resp,
        "is_complete":    True,
        "messages": [{
            "role":    "assistant",
            "content": f"{coach_resp.headline}\n\n{coach_resp.explanation}",
        }],
        "stream_events": stream_events,
    }


def _build_fallback_response(correlation: Any, confidence: float) -> CoachResponse:
    """Plain-text fallback when LLM JSON parsing fails."""
    chain_text = " → ".join(correlation.causal_chain[:3]) if correlation.causal_chain else "See findings above."
    return CoachResponse(
        headline=f"Found pattern: {correlation.pattern_title}",
        explanation=chain_text,
        action_items=[
            "Review your Tuesday training intensity.",
            "Eat more before and after Tuesday workouts.",
            "Move your last meal to before 20:00 on training days.",
        ],
        domains_cited=correlation.involved_domains,
        correlation=correlation,
    )