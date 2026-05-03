## VitalSync — personal health pattern orchestrator

Agents analyze mock vitals (sleep, activity, stress, nutrition). They flag correlations across domains and surface insights the user hasn't noticed — with full agent reasoning shown.
Agents: sleep analyst, activity agent, nutrition agent, correlator, coach

VitalSync — personal health pattern orchestrator
Why it's uncommon: Correlation across domains is the hard part — agents first analyze their own domain, then the correlator agent synthesizes cross-domain patterns humans miss.

Architecture:
• Mock health data generator produces realistic 90-day histories per domain
• Domain agents run analyses independently, output structured insight objects
• Correlator agent receives all outputs and runs a second-pass synthesis
• Coach agent turns insights into actionable recommendations
• MCP server exposes health data tools + Open-Meteo weather (correlate sleep with weather)

Free APIs: Open-Meteo (free, for weather correlation), rest is mock data

Interesting twist: Users can ask "why do I sleep badly on Tuesdays?" and watch agents collaboratively trace the cause across domains.

## Backend quick start

1. Create a Python virtualenv and install dependencies from `backend/requirements.txt`.

```bash
python -m venv venv
venv\Scripts\activate   # Windows
pip install -r backend/requirements.txt
```

2. Run the FastAPI backend with Uvicorn (from repo root):

```bash
uvicorn backend.main:app --reload --port 8000
```

3. Development notes:

- The MCP server tools are mounted under `/mcp/tools/...` and return mock data.
- The API query endpoint is `/api/query` and accepts JSON `{ "query": "..." }`.
- The websocket endpoint is at `/api/ws` if you wire it in a frontend; the included handler expects a JSON message with `query`.
