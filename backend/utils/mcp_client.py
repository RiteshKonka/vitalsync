"""
utils/mcp_client.py
───────────────────
MCP stdio client used by agents to call tools on the MCP server.

Architecture
────────────
The MCP server (mcp_server/server.py) runs as a subprocess.
Agents call tools by name through this client, which handles the
stdio transport and JSON-RPC protocol.

Two modes
─────────
1. LIVE mode  — spawns mcp_server/server.py as a subprocess and
               communicates over stdio (real MCP protocol).
               Used in production when MCP_MODE=live in .env.

2. DIRECT mode (default) — calls mock_data functions directly,
               bypassing the subprocess entirely.
               Used during development so the backend runs without
               the MCP server process.

Agents always call `call_tool(name, **kwargs)` — they don't know
which mode is active. Switching from DIRECT → LIVE is one env var.

Usage in base_agent.py:
    from utils.mcp_client import call_tool
    data = call_tool("get_sleep_data")
    pattern = call_tool("get_weekly_pattern", domain="sleep", metric="deep_sleep_pct")
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import subprocess
from pathlib import Path
from typing import Any

from .logger import get_logger

logger = get_logger(__name__)

# ── Mode detection ────────────────────────────────────────────────

MCP_MODE = os.getenv("MCP_MODE", "direct").lower()   # "direct" | "live"

# ── Direct-mode routing table ─────────────────────────────────────
# Maps tool name → (module_path, function_name)
# Loaded lazily so we don't import everything at module level.

_DIRECT_ROUTES: dict[str, tuple[str, str]] = {
    "get_sleep_data":           ("backend.mock_data.generator",          "get_data"),
    "get_activity_data":        ("backend.mock_data.generator",          "get_data"),
    "get_nutrition_data":       ("backend.mock_data.generator",          "get_data"),
    "get_stress_data":          ("backend.mock_data.generator",          "get_data"),
    "get_weather_data":         ("backend.mcp_server.tools.weather_tools", "get_weather_data"),
    "get_weekly_pattern":       ("backend.mock_data.generator",          "get_weekly_pattern"),
    "get_domain_summary":       ("backend.mock_data.generator",          "get_domain_summary"),
    "get_all_domains_summary":  ("backend.mcp_server.tools.health_tools", "get_all_domains_summary"),
    "get_user_profile":         ("backend.mcp_server.tools.coach_tools", "get_user_profile"),
    "save_insight":             ("backend.mcp_server.tools.coach_tools", "save_insight"),
    "get_saved_insights":       ("backend.mcp_server.tools.coach_tools", "get_saved_insights"),
    "mark_insight_resolved":    ("backend.mcp_server.tools.coach_tools", "mark_insight_resolved"),
    "get_weather_weekly_pattern": ("backend.mcp_server.tools.weather_tools", "get_weather_weekly_pattern"),
}

# Domain-mapping tools (get_data needs a domain arg derived from tool name)
_DOMAIN_MAP: dict[str, str] = {
    "get_sleep_data":     "sleep",
    "get_activity_data":  "activity",
    "get_nutrition_data": "nutrition",
    "get_stress_data":    "stress",
}


def _call_direct(tool_name: str, **kwargs) -> Any:
    """
    Calls the underlying function directly without any subprocess.
    This is fast, synchronous, and works with zero infrastructure.
    """
    import importlib

    if tool_name not in _DIRECT_ROUTES:
        raise ValueError(f"Unknown MCP tool: '{tool_name}'")

    module_path, fn_name = _DIRECT_ROUTES[tool_name]
    try:
        module = importlib.import_module(module_path)
    except Exception:
        # Try adding or removing leading 'backend.' to support running
        # from repo root (package) or from within the backend/ folder.
        alt = None
        if module_path.startswith("backend."):
            alt = module_path[len("backend."):]
        else:
            alt = f"backend.{module_path}"
        module = importlib.import_module(alt)

    fn = getattr(module, fn_name)

    # For get_data(domain) calls, inject the domain from the tool name
    if tool_name in _DOMAIN_MAP and not kwargs.get("domain"):
        kwargs["domain"] = _DOMAIN_MAP[tool_name]
        return fn(**kwargs)

    return fn(**kwargs)


# ── Live MCP subprocess client ────────────────────────────────────

_server_proc: subprocess.Popen | None = None
_server_lock = asyncio.Lock() if asyncio.get_event_loop().is_running() else None


def _get_server_path() -> Path:
    """Resolves path to mcp_server/server.py relative to this file."""
    return Path(__file__).parent.parent / "mcp_server" / "server.py"


def _ensure_server() -> subprocess.Popen:
    """Starts the MCP server subprocess if not already running."""
    global _server_proc
    if _server_proc and _server_proc.poll() is None:
        return _server_proc   # still alive

    server_path = _get_server_path()
    logger.info("Starting MCP server subprocess: %s", server_path)
    _server_proc = subprocess.Popen(
        ["python", str(server_path)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )
    logger.info("MCP server started (pid=%d)", _server_proc.pid)
    return _server_proc


def _call_live(tool_name: str, **kwargs) -> Any:
    """
    Sends a JSON-RPC tool call to the MCP server over stdio.
    This implements the MCP protocol's tools/call method.
    """
    proc = _ensure_server()

    request = {
        "jsonrpc": "2.0",
        "id":      1,
        "method":  "tools/call",
        "params":  {
            "name":      tool_name,
            "arguments": kwargs,
        },
    }

    try:
        proc.stdin.write(json.dumps(request) + "\n")
        proc.stdin.flush()
        raw = proc.stdout.readline()
        response = json.loads(raw)

        if "error" in response:
            raise RuntimeError(f"MCP error: {response['error']}")

        result = response.get("result", {})
        # MCP returns content as list of {type, text} blocks
        if isinstance(result, dict) and "content" in result:
            content = result["content"]
            if isinstance(content, list) and content:
                text = content[0].get("text", "")
                return json.loads(text)
        return result

    except Exception as e:
        logger.error("MCP live call failed for '%s': %s", tool_name, e)
        # Fall back to direct mode on any transport error
        logger.warning("Falling back to direct mode for '%s'", tool_name)
        return _call_direct(tool_name, **kwargs)


# ── Public API ────────────────────────────────────────────────────

def call_tool(tool_name: str, **kwargs) -> Any:
    """
    Main entry point for agents. Calls the named MCP tool.

    Args:
        tool_name: one of the tool names registered on the MCP server
        **kwargs:  tool arguments

    Returns:
        Tool result (list, dict, bool etc.)

    Raises:
        ValueError: if tool_name is not registered
        RuntimeError: if live MCP call fails and fallback also fails
    """
    logger.debug("call_tool('%s', %s) [mode=%s]", tool_name, kwargs, MCP_MODE)

    if MCP_MODE == "live":
        return _call_live(tool_name, **kwargs)
    else:
        return _call_direct(tool_name, **kwargs)


def shutdown_server() -> None:
    """Terminates the MCP server subprocess if running."""
    global _server_proc
    if _server_proc and _server_proc.poll() is None:
        logger.info("Shutting down MCP server (pid=%d)", _server_proc.pid)
        _server_proc.terminate()
        try:
            _server_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _server_proc.kill()
        _server_proc = None