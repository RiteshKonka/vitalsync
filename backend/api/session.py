"""
api/session.py
──────────────
In-memory session store keyed by session_id (UUID from the browser).
Stores query history and the last graph state per session.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class Session:
    session_id:    str
    created_at:    float = field(default_factory=time.time)
    last_active:   float = field(default_factory=time.time)
    query_history: list[dict] = field(default_factory=list)
    last_state:    Optional[Any] = None

    def touch(self):
        self.last_active = time.time()

    def add_query(self, query: str, response: dict):
        self.query_history.append({
            "query":     query,
            "response":  response,
            "timestamp": time.time(),
        })
        self.touch()


_sessions: dict[str, Session] = {}


def get_or_create(session_id: str) -> Session:
    if session_id not in _sessions:
        _sessions[session_id] = Session(session_id=session_id)
    return _sessions[session_id]


def get(session_id: str) -> Optional[Session]:
    return _sessions.get(session_id)


def cleanup_old(max_age_seconds: int = 3600) -> int:
    now   = time.time()
    stale = [sid for sid, s in _sessions.items()
             if now - s.last_active > max_age_seconds]
    for sid in stale:
        del _sessions[sid]
    return len(stale)