"""
utils/groq_client.py
────────────────────
Singleton Groq client with streaming support.

All agents use get_groq_client() to get the shared client instance.
stream_agent_response() is the primary helper — it yields token chunks
and also builds the full response string for structured parsing.

Models available on Groq free tier (as of 2025):
  - llama-3.3-70b-versatile  ← default, best reasoning
  - llama-3.1-8b-instant     ← fast, for lightweight calls
  - mixtral-8x7b-32768       ← large context window
"""

from __future__ import annotations

import os
import logging
from typing import Generator, Optional
from groq import Groq

logger = logging.getLogger(__name__)

_client: Optional[Groq] = None

DEFAULT_MODEL   = "llama-3.3-70b-versatile"
FAST_MODEL      = "llama-3.1-8b-instant"
MAX_TOKENS      = 1024


def get_groq_client() -> Groq:
    """Returns the shared Groq client, creating it on first call."""
    global _client
    if _client is None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError("GROQ_API_KEY environment variable not set")
        _client = Groq(api_key=api_key)
        logger.info("Groq client initialised (model: %s)", DEFAULT_MODEL)
    return _client


def stream_agent_response(
    messages:    list[dict],
    system:      str,
    model:       str = DEFAULT_MODEL,
    temperature: float = 0.3,
    max_tokens:  int = MAX_TOKENS,
) -> Generator[str, None, str]:
    """
    Streams a Groq completion token by token.

    Usage in an agent:
        full_text = ""
        for chunk in stream_agent_response(messages, system):
            full_text += chunk
            # emit chunk as StreamEvent to state

    Yields: token strings (may be multi-character chunks)
    Returns (via StopIteration value): the full accumulated response
    """
    client = get_groq_client()
    full_text = ""

    try:
        stream = client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": system}] + messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )
        for chunk in stream:
            delta = chunk.choices[0].delta.content or ""
            if delta:
                full_text += delta
                yield delta

    except Exception as e:
        logger.error("Groq stream error: %s", e)
        yield f"[ERROR: {e}]"

    return full_text


def complete(
    messages:    list[dict],
    system:      str,
    model:       str = DEFAULT_MODEL,
    temperature: float = 0.1,
    max_tokens:  int = MAX_TOKENS,
    json_mode:   bool = False,
) -> str:
    """
    Non-streaming completion. Used for structured JSON outputs
    (supervisor query parse, confidence scoring).
    """
    client = get_groq_client()
    kwargs = dict(
        model=model,
        messages=[{"role": "system", "content": system}] + messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    response = client.chat.completions.create(**kwargs)
    return response.choices[0].message.content or ""