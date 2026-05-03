"""
utils/logger.py
───────────────
Structured logging for VitalSync.

Provides:
  - get_logger(name)            standard logger with consistent format
  - get_agent_logger(agent)     logger pre-tagged with agent name
  - AgentLogAdapter             adds 'agent' key to every log record
  - log_stream_event()          one-liner to log a StreamEvent
  - log_insight()               one-liner to log an InsightMessage summary
  - TimedBlock                  context manager for timing code blocks

All loggers write to stdout so Docker/uvicorn can capture them.
In production, swap the handler for a JSON formatter + log aggregator.
"""

from __future__ import annotations

import logging
import sys
import time
from contextlib import contextmanager
from typing import Generator


# ── Formatter ─────────────────────────────────────────────────────

LOG_FORMAT  = "%(asctime)s [%(levelname)-8s] %(name)s: %(message)s"
DATE_FORMAT = "%H:%M:%S"


def _build_handler() -> logging.StreamHandler:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))
    return handler


# ── Root setup (called once from main.py) ─────────────────────────

def setup_logging(level: int = logging.INFO) -> None:
    """
    Call once at application startup.
    main.py already calls basicConfig; this is an explicit override
    that ensures our format wins even if a library reconfigures root.
    """
    root = logging.getLogger()
    root.setLevel(level)
    # Remove any existing handlers to avoid duplicate output
    root.handlers.clear()
    root.addHandler(_build_handler())

    # Quiet noisy third-party loggers
    for noisy in ("httpx", "httpcore", "groq", "urllib3"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


# ── Per-module logger ─────────────────────────────────────────────

def get_logger(name: str) -> logging.Logger:
    """Standard logger. Usage: logger = get_logger(__name__)"""
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.addHandler(_build_handler())
        logger.propagate = False
    return logger


# ── Agent-scoped logger ───────────────────────────────────────────

class AgentLogAdapter(logging.LoggerAdapter):
    """
    Prepends [agent_name] to every message so agent logs are
    easy to grep in combined output.

    Usage:
        logger = get_agent_logger(AgentName.SLEEP)
        logger.info("deep sleep anomaly found")
        # → 12:34:56 [INFO    ] agents.sleep: [sleep] deep sleep anomaly found
    """

    def process(self, msg: str, kwargs: dict) -> tuple[str, dict]:
        agent = self.extra.get("agent", "unknown")
        return f"[{agent}] {msg}", kwargs


def get_agent_logger(agent_name: str) -> AgentLogAdapter:
    """
    Returns a logger pre-tagged with the agent name.
    agent_name should be the AgentName.value string e.g. "sleep".
    """
    base = logging.getLogger(f"agents.{agent_name}")
    return AgentLogAdapter(base, {"agent": agent_name})


# ── Convenience log helpers ───────────────────────────────────────

def log_stream_event(logger: logging.Logger, event) -> None:
    """
    Logs a StreamEvent in a compact one-line format.
    Accepts any object with .event_type, .agent, .content attributes.
    """
    logger.debug(
        "StreamEvent | type=%-16s agent=%-12s content=%.80s",
        getattr(event.event_type, "value", event.event_type),
        getattr(event.agent, "value", event.agent),
        event.content,
    )


def log_insight(logger: logging.Logger, insight) -> None:
    """
    Logs an InsightMessage summary in a compact one-line format.
    """
    logger.info(
        "InsightMessage | agent=%-12s confidence=%.0f%% anomalies=%d summary=%.80s",
        getattr(insight.agent, "value", insight.agent),
        insight.confidence * 100,
        len(insight.anomalies),
        insight.summary,
    )


def log_correlation(logger: logging.Logger, result) -> None:
    """Logs a CorrelationResult summary."""
    logger.info(
        "Correlation | pattern='%s' confidence=%.0f%% domains=%s",
        result.pattern_title,
        result.confidence * 100,
        [getattr(d, "value", d) for d in result.involved_domains],
    )


# ── Timing context manager ─────────────────────────────────────────

@contextmanager
def TimedBlock(label: str, logger: logging.Logger | None = None) -> Generator:
    """
    Times a block of code and logs the duration.

    Usage:
        with TimedBlock("graph.invoke", logger):
            result = graph.invoke(state)
        # → [graph.invoke] completed in 3.42s
    """
    _logger = logger or get_logger("vitalsync.timing")
    start = time.perf_counter()
    try:
        yield
    finally:
        elapsed = time.perf_counter() - start
        _logger.info("[%s] completed in %.2fs", label, elapsed)