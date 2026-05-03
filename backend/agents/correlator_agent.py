"""
agents/correlator_agent.py
──────────────────────────
The correlator is the heart of VitalSync's multi-agent value.

It does NOT call any MCP tools or look at raw data.
It reads only the InsightMessages written by the domain agents — the A2A bus.
Its job is to find causal chains that span multiple domains.

This is why you need multi-agent: no single domain agent sees all of these.
The correlator sees all InsightMessages simultaneously and can reason
about interactions between sleep, training load, nutrition, stress, and weather.

Output: a CorrelationResult written to state, plus a confidence_score.
If confidence < CONFIDENCE_THRESHOLD, the supervisor will retry weak agents.
"""

from __future__ import annotations
import json
import logging
from typing import Any

from ..orchestrator.state import (
    VitalSyncState,
    AgentName,
    CorrelationResult,
    StreamEvent,
    StreamEventType,
    CONFIDENCE_THRESHOLD,
)
from ..utils.groq_client import complete

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are the Correlation Analysis Agent for VitalSync — the synthesis layer of a multi-agent health intelligence system.

You receive structured findings (InsightMessages) from 5 specialist agents:
  - sleep:     sleep architecture, HRV, deep sleep quality
  - activity:  training load, workout intensity
  - nutrition: caloric balance, meal timing
  - stress:    resting HR, morning HRV, recovery score
  - weather:   environmental conditions

Your job is to find the CAUSAL CHAIN connecting the findings.
Ask: "What sequence of events explains the user's symptom?"

Rules:
1. Prioritise explanations that involve multiple agents over single-domain explanations.
2. The causal_chain should be an ordered list of cause → effect steps.
3. Be specific — use the actual metric values from the InsightMessages.
4. List alternative_hypotheses if other explanations are plausible.
5. Score confidence based on: number of corroborating agents, consistency of evidence, strength of each finding.
6. Confidence > 0.85 means you are very sure. 0.60–0.85 means likely but uncertain. < 0.60 means weak evidence.

Return ONLY valid JSON matching this structure exactly:
{
  "pattern_title": "short name for the pattern",
  "causal_chain": [
    "Step 1: ...",
    "Step 2: ...",
    ...
  ],
  "involved_domains": ["sleep", "activity", "nutrition", "stress"],
  "supporting_metrics": {
    "domain_name": {"metric": value, ...},
    ...
  },
  "confidence": float,
  "alternative_hypotheses": ["other possible explanations"]
}"""


def _format_insights_for_llm(insights: list) -> str:
    """
    Formats all InsightMessages into a compact LLM-readable block.
    """
    lines = []
    for msg in insights:
        lines.append(f"\n=== {msg.agent.value.upper()} AGENT (confidence: {msg.confidence:.0%}) ===")
        lines.append(f"Summary: {msg.summary}")
        lines.append(f"Key metrics: {json.dumps(msg.key_metrics, indent=2)}")
        lines.append(f"Anomalies: {msg.anomalies}")
    return "\n".join(lines)


def run(state: VitalSyncState) -> dict:
    """
    Correlator node. Reads InsightMessages, writes CorrelationResult.
    Returns partial state update.
    """
    stream_events: list[StreamEvent] = []
    insights = state.get("insight_messages", [])
    query    = state.get("query", "")

    stream_events.append(StreamEvent(
        event_type=StreamEventType.AGENT_START,
        agent=AgentName.CORRELATOR,
        content=f"Correlator reading {len(insights)} agent insights...",
    ))

    if not insights:
        logger.warning("Correlator: no InsightMessages received")
        return {
            "confidence_score": 0.1,
            "should_retry": False,
            "stream_events": stream_events,
        }

    formatted = _format_insights_for_llm(insights)

    prompt = f"""
The user asked: "{query}"

Here are the findings from all domain agents:

{formatted}

Now identify the causal chain that best explains the user's question.
Connect the dots across domains. Return JSON only.
"""

    raw = complete(
        messages=[{"role": "user", "content": prompt}],
        system=SYSTEM_PROMPT,
        temperature=0.2,
        max_tokens=1000,
        json_mode=True,
    )

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("Correlator: JSON parse failed")
        data = {}

    # Build CorrelationResult
    if data.get("pattern_title"):
        involved = []
        for d in data.get("involved_domains", []):
            try:
                involved.append(AgentName(d))
            except ValueError:
                pass

        correlation = CorrelationResult(
            pattern_title=data["pattern_title"],
            causal_chain=data.get("causal_chain", []),
            involved_domains=involved,
            supporting_metrics=data.get("supporting_metrics", {}),
            confidence=float(data.get("confidence", 0.5)),
            alternative_hypotheses=data.get("alternative_hypotheses", []),
        )
    else:
        # Fallback: build from raw insights if LLM failed
        correlation = _build_fallback_correlation(insights, query)

    confidence = correlation.confidence
    should_retry = confidence < CONFIDENCE_THRESHOLD

    stream_events.append(StreamEvent(
        event_type=StreamEventType.CORRELATION,
        agent=AgentName.CORRELATOR,
        content=f"Pattern found: {correlation.pattern_title} (confidence: {confidence:.0%})",
        metadata={
            "pattern_title":    correlation.pattern_title,
            "causal_chain":     correlation.causal_chain,
            "involved_domains": [a.value for a in correlation.involved_domains],
            "confidence":       confidence,
            "should_retry":     should_retry,
        },
    ))

    logger.info(
        "Correlator: '%s' (confidence: %.2f, retry: %s)",
        correlation.pattern_title, confidence, should_retry,
    )

    return {
        "correlation_result": correlation,
        "confidence_score":   confidence,
        "should_retry":       should_retry,
        "stream_events":      stream_events,
    }


def _build_fallback_correlation(insights: list, query: str) -> CorrelationResult:
    """
    Rule-based fallback when LLM fails. Constructs a basic correlation
    from whichever agents reported the highest-confidence anomalies.
    """
    sorted_insights = sorted(insights, key=lambda m: m.confidence, reverse=True)
    top_agents      = [m.agent for m in sorted_insights[:3]]
    top_anomalies   = [a for m in sorted_insights[:3] for a in m.anomalies[:1]]
    avg_confidence  = sum(m.confidence for m in sorted_insights[:3]) / max(1, len(sorted_insights[:3]))

    return CorrelationResult(
        pattern_title="Multi-domain fatigue pattern",
        causal_chain=[f"Evidence from {a.value}: {m.summary}" for a, m in zip(top_agents, sorted_insights[:3])],
        involved_domains=top_agents,
        supporting_metrics={m.agent.value: m.key_metrics for m in sorted_insights[:3]},
        confidence=round(avg_confidence * 0.85, 2),   # discount for fallback
        alternative_hypotheses=["Single-domain cause not yet ruled out"],
    )