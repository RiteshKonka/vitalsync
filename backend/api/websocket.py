"""
api/websocket.py
────────────────
WebSocket endpoint — the live nerve of the frontend.

Protocol (client → server):
    { "type": "query", "session_id": "uuid", "query": "why am I tired?" }

Protocol (server → client), one JSON frame per event:
    { "type": "processing",    "content": "Activating agents..." }
    { "type": "agent_start",   "agent": "sleep",  "content": "..." }
    { "type": "agent_thought", "agent": "sleep",  "content": "token chunk" }
    { "type": "tool_call",     "agent": "sleep",  "content": "...", "metadata": {...} }
    { "type": "a2a_message",   "agent": "sleep",  "content": "...", "metadata": {...} }
    { "type": "correlation",   "agent": "correlator", "content": "...", "metadata": {...} }
    { "type": "final_answer",  "agent": "coach",  "content": "...", "metadata": {...} }
    { "type": "done",          "session_id": "uuid" }
    { "type": "error",         "message": "..." }

The graph runs synchronously in a threadpool (asyncio.to_thread) so
it does not block FastAPI's event loop.
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
# Ensure project root (parent of backend/) is on sys.path so
# `import backend...` works even when running from backend/.

from fastapi            import APIRouter, WebSocket, WebSocketDisconnect
try:
    from ..orchestrator.graph  import vitalsync_graph
    from ..orchestrator.state  import initial_state
except Exception:
    try:
        from orchestrator.graph  import vitalsync_graph
        from orchestrator.state  import initial_state
    except Exception:
        from backend.orchestrator.graph import vitalsync_graph
        from backend.orchestrator.state import initial_state

try:
    from .session             import get_or_create
except Exception:
    from api.session import get_or_create

logger = logging.getLogger(__name__)
router = APIRouter()


def _run_graph(query: str, session_id: str) -> dict:
    """Blocking call — runs in threadpool via asyncio.to_thread."""
    state  = initial_state(query=query, session_id=session_id)
    result = vitalsync_graph.invoke(state)
    return result


async def _drain_events(state: dict, ws: WebSocket) -> None:
    """Send every StreamEvent in state to the WebSocket client."""
    for event in state.get("stream_events", []):
        frame = {
            "type":      event.event_type.value,
            "agent":     event.agent.value,
            "content":   event.content,
            "metadata":  event.metadata,
            "timestamp": event.timestamp.isoformat(),
        }
        await ws.send_text(json.dumps(frame))
        await asyncio.sleep(0.008)   # breathing room between frames


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    logger.info("WebSocket connected")

    try:
        while True:
            raw = await websocket.receive_text()

            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({"type": "error", "message": "Invalid JSON"}))
                continue

            if msg.get("type") != "query":
                continue

            query      = msg.get("query", "").strip()
            session_id = msg.get("session_id", "default")

            if not query:
                await websocket.send_text(json.dumps({"type": "error", "message": "Empty query"}))
                continue

            session = get_or_create(session_id)
            logger.info("Query [%s]: %s", session_id[:8], query)

            # Tell the UI we're starting
            await websocket.send_text(json.dumps({
                "type":    "processing",
                "content": "Activating agents...",
            }))

            # Run the full agent graph in a thread (non-blocking)
            try:
                final_state = await asyncio.to_thread(_run_graph, query, session_id)
            except Exception as exc:
                logger.error("Graph error: %s", exc, exc_info=True)
                await websocket.send_text(json.dumps({
                    "type":    "error",
                    "message": f"Analysis failed: {exc}",
                }))
                continue

            # Stream every event the agents produced
            await _drain_events(final_state, websocket)

            # Persist to session
            coach = final_state.get("coach_response")
            if coach:
                session.add_query(query, {
                    "headline":     coach.headline,
                    "explanation":  coach.explanation,
                    "action_items": coach.action_items,
                    "domains_cited": [a.value for a in coach.domains_cited],
                })
            session.last_state = final_state

            # Signal done
            await websocket.send_text(json.dumps({
                "type":       "done",
                "session_id": session_id,
            }))
            logger.info("Done [%s]", session_id[:8])

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except Exception as exc:
        logger.error("WebSocket unhandled error: %s", exc, exc_info=True)
        try:
            await websocket.send_text(json.dumps({"type": "error", "message": str(exc)}))
        except Exception:
            pass