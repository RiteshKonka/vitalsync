"""
main.py
───────
VitalSync FastAPI application.

Start with:
    cd backend
    uvicorn main:app --reload --port 8000

Endpoints:
    REST   http://localhost:8000/api/...
    WS     ws://localhost:8000/ws
    Docs   http://localhost:8000/docs
"""

from __future__ import annotations

import logging
import os
import sys

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

# Ensure parent directory (repo root) is on sys.path so `import backend...`
# works when running from the `backend/` directory.
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# If this file is run as a script ("python main.py" from inside backend/),
# re-import it as a package module so relative imports work consistently.
if __package__ is None:
    import os, sys, importlib
    parent = os.path.dirname(os.path.dirname(__file__))
    if parent not in sys.path:
        sys.path.insert(0, parent)
    importlib.import_module("backend.main")
    # Imported as package; exit the script-run invocation.
    raise SystemExit()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ───────────────────────────────────────────────────
    logger.info("VitalSync starting up...")

    # Pre-warm mock data cache
    try:
        from backend.mock_data.generator import get_data
    except Exception:
        from .mock_data.generator import get_data
    for domain in ["sleep", "activity", "nutrition", "stress", "weather"]:
        get_data(domain)
    logger.info("  ✓ Mock data loaded (5 domains × 90 days)")

    # Compile LangGraph graph once — validates all node wiring
    try:
        from backend.orchestrator.graph import vitalsync_graph  # noqa: F401
    except Exception:
        from .orchestrator.graph import vitalsync_graph  # noqa: F401
    logger.info("  ✓ LangGraph graph compiled")

    # Warn if no Groq key
    if not os.getenv("GROQ_API_KEY"):
        logger.warning("  ⚠  GROQ_API_KEY not set — LLM calls will fail at runtime")
    else:
        logger.info("  ✓ GROQ_API_KEY present")

    logger.info("VitalSync ready → http://localhost:8000  |  ws://localhost:8000/ws")
    yield

    # ── Shutdown ──────────────────────────────────────────────────
    logger.info("VitalSync shutting down")


app = FastAPI(
    title="VitalSync API",
    description="Multi-agent personal health intelligence",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",   # Vite dev server
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers (support running as package or as a script)
try:
    from .api.routes    import router as rest_router
    from .api.websocket import router as ws_router
except Exception:
    # Fallback when __package__ is not set (running as script from backend/)
    from api.routes    import router as rest_router
    from api.websocket import router as ws_router

app.include_router(rest_router, prefix="/api")
app.include_router(ws_router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "vitalsync"}