"""
mcp_server/server.py
────────────────────
VitalSync MCP tool server.

Registers all health, weather and coach tools via FastMCP.
Agents connect to this server over stdio and call tools by name.

To run standalone:
    cd backend && python -m mcp_server.server

How agents use it (in production):
    - mcp_client.py spawns this process at startup
    - Agents call _call_tool("get_sleep_data") etc.
    - For now, base_agent.py calls mock_data directly (same data)
      so the stack works without the subprocess running.
"""

from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp.server.fastmcp import FastMCP

from mcp_server.tools.health_tools  import (
    get_sleep_data, get_activity_data,
    get_nutrition_data, get_stress_data,
    get_weekly_pattern_tool, get_domain_summary_tool,
    get_all_domains_summary,
)
from mcp_server.tools.weather_tools import (
    get_weather_data, get_weather_weekly_pattern,
)
from mcp_server.tools.coach_tools   import (
    get_user_profile, save_insight,
    get_saved_insights, mark_insight_resolved,
)

mcp = FastMCP("vitalsync-health-tools")

# ── Health tools ──────────────────────────────────────────────────

@mcp.tool()
def tool_get_sleep_data() -> list[dict]:
    """90 days of sleep: total_hours, deep_sleep_pct, hrv_ms, sleep_score."""
    return get_sleep_data()

@mcp.tool()
def tool_get_activity_data() -> list[dict]:
    """90 days of activity: steps, workout_minutes, training_load, zone3/4_minutes."""
    return get_activity_data()

@mcp.tool()
def tool_get_nutrition_data() -> list[dict]:
    """90 days of nutrition: total_kcal, caloric_balance, last_meal_time, macros."""
    return get_nutrition_data()

@mcp.tool()
def tool_get_stress_data() -> list[dict]:
    """90 days of stress: resting_hr_bpm, hrv_morning_ms, recovery_score."""
    return get_stress_data()

@mcp.tool()
def tool_get_weekly_pattern(domain: str, metric: str) -> dict[str, float]:
    """Day-of-week averages for any domain metric."""
    return get_weekly_pattern_tool(domain, metric)

@mcp.tool()
def tool_get_domain_summary(domain: str) -> dict:
    """Aggregate stats + day-of-week breakdown for a domain."""
    return get_domain_summary_tool(domain)

@mcp.tool()
def tool_get_all_domains_summary() -> dict:
    """Summaries for all 5 domains in one call."""
    return get_all_domains_summary()

# ── Weather tools ─────────────────────────────────────────────────

@mcp.tool()
def tool_get_weather_data() -> list[dict]:
    """90 days Mumbai weather. Uses Open-Meteo when available, mock as fallback."""
    return get_weather_data()

@mcp.tool()
def tool_get_weather_weekly_pattern() -> dict[str, dict[str, float]]:
    """Day-of-week weather averages: temperature, rain, humidity."""
    return get_weather_weekly_pattern()

# ── Coach tools ───────────────────────────────────────────────────

@mcp.tool()
def tool_get_user_profile(session_id: str = "default") -> dict:
    """User health profile: age, weight, TDEE, HRV baseline, goals."""
    return get_user_profile(session_id)

@mcp.tool()
def tool_save_insight(session_id: str, headline: str, explanation: str,
                      action_items: list[str], domains: list[str]) -> dict:
    """Persists a coach insight to session history."""
    return save_insight(session_id, headline, explanation, action_items, domains)

@mcp.tool()
def tool_get_saved_insights(session_id: str) -> list[dict]:
    """Returns all saved insights for a session."""
    return get_saved_insights(session_id)

@mcp.tool()
def tool_mark_insight_resolved(session_id: str, insight_id: str) -> bool:
    """Marks an insight as resolved."""
    return mark_insight_resolved(session_id, insight_id)

if __name__ == "__main__":
    mcp.run()