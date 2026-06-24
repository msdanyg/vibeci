# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

**VibeCI** — a multi-agent competitive-intelligence web app (Kaggle "AI Agents: Intensive Vibe Coding" capstone). A user submits a competitor + a documentation URL + the competitor's marketing claims + their own positioning; a pipeline of agents reads the competitor's technical docs, surfaces gaps between marketing claims and documented reality, and returns a structured sales battle card. The **Technical Analysis Agent is the deliberate centerpiece** (per `01_MISSION_CHARTER.md`) — discovery/monitoring is treated as commodity; the differentiator is contrasting claims vs. docs. Keep that emphasis when extending.

## Commands

No linter or build step is configured. There **is** a pytest suite (`tests/`) covering the deterministic core — the MCP tools and the demo pipeline / SSE event contract (live agents are not exercised, since they need a quota-enabled key). Common workflows:

```bash
# Setup (Python 3.11+)
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Tests — run from the repo root (TestClient + StaticFiles use relative paths)
pip install -r requirements-dev.txt
pytest                       # whole suite
pytest tests/test_api.py -q  # one file
pytest -k grounding -q       # one pattern

# Run locally — MUST be from the repo root (see gotchas)
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
# → http://localhost:8080

# Docker
docker build -t vibeci .
docker run -p 8080:8080 -e GEMINI_API_KEY=your_key vibeci

# Deploy to Cloud Run — use the wrapper (it pins CLOUDSDK_PYTHON to the venv)
./gcloud.sh run deploy vibeci --image gcr.io/PROJECT_ID/vibeci --region us-central1 ...
```

`GEMINI_API_KEY` lives in `.env` (loaded via `python-dotenv`). It is required for **live mode only** — demo mode runs with no key and no network; the gate is in `app/main.py`. Live mode also needs a **quota-enabled** key (the Gemini free tier can be `0` for `gemini-2.0-flash` → a 429; the UI surfaces this gracefully with a demo-mode fallback).

## Architecture

**SDK note:** despite the README calling it "Google ADK," the code uses the **`google.antigravity`** SDK (`from google.antigravity import Agent, LocalAgentConfig`). All agents target `gemini-2.0-flash` (set once in `app/agents/config.py:DEFAULT_MODEL`).

### Request lifecycle
1. `POST /api/analyze` → creates a job (UUID), kicks off `execute_workflow` as a FastAPI `BackgroundTask`, returns `job_id`.
2. Frontend opens `GET /api/stream/{job_id}` as an SSE `EventSource`. `execute_workflow` emits a **structured timeline of typed events** (not log strings): `mode`, `pipeline` (the four-agent manifest from `config.agent_manifest()` — label/specialty/capability/reasoning-level/accent; `app.js` builds the timeline rows from this), `agent` (`phase: start|done`, with `detail`/`elapsed_ms` — **elapsed only in live mode**; demo sends `null` → "Done"), `tool` (real MCP call name + args + result), `doc` (the ingested `raw_doc` for the live source panel), and a terminal `completed` (full report) / `failed`. The client (`app.js`) renders these as the run-timeline; changing an event shape means updating both sides.
3. Job state lives in two **in-memory module-level dicts** in `app/main.py`: `jobs` (status/**`events`**/result) and `queues` (per-job `asyncio.Queue` feeding the SSE stream). Lost on restart and **not safe across multiple workers** — run uvicorn single-process. The stream replays `jobs[id]["events"]` only if the job already finished before the client connected; otherwise it drains the queue live (sole producer/consumer, so no dup/miss).

### The agent pipeline (`execute_workflow` in `app/main.py`)
Orchestration is **manual sequential `await`s**, not SDK-driven multi-agent handoff. The four agents run in order, each `app/agents/<name>.py` exposing one `run_*_agent(...)` coroutine:

`discovery` → `analysis` ★ → `synthesis` → `checking`

- **discovery.py** — only agent that uses the MCP server *as* an MCP server (spawns `app.mcp_server` over stdio via `McpStdioServer`). Returns a cleaned markdown spec summary.
- **analysis.py** ★ — the star. Contrasts doc summary vs. marketing claims vs. own positioning. Plain text out.
- **synthesis.py** — defines the Pydantic output schema (`CompetitorReport` → `BattleCard`, `ClaimGap`, `ObjectionHandler`) and emits structured JSON via `response_schema`.
- **checking.py** — fact-checks the draft report against the raw specs, re-validates against `CompetitorReport`, falls back to the unmodified draft if parsing fails.

`app/agents/config.py` centralizes everything: `AGENT_SPECS` (per-agent persona, **real `ThinkingLevel`** — discovery `low`, analysis/checking `high`, synthesis `medium` — plus UI metadata: specialty/capability/accent/star), `agent_manifest()` (secret-free metadata for the `pipeline` SSE event), and `get_agent_config(persona_type, tools, response_schema, mcp_servers, api_key)` which builds a specialized `LocalAgentConfig` (a `ModelTarget` whose `GeminiAPIEndpoint` carries the thinking level + the bring-your-own-key). Each `run_*_agent(...)` takes an `api_key` and forwards it. Add new agents/personas here.

### MCP tools have two invocation paths (`app/mcp_server.py`)
`fetch_competitor_docs` and `compare_claims_to_docs` are exposed via `FastMCP` over stdio, **but** `app/main.py` also imports them as plain Python functions and calls them directly in the live path (for the `raw_doc` and `preliminary_gaps` that get appended to the result). Only the Discovery agent reaches them through the MCP transport. `fetch_competitor_docs` tries a live HTTP GET, then falls back to `MOCK_DOCUMENTS` keyed by competitor name substring.

### Two execution modes
- **Demo mode** (`demo_mode: true`, UI default) — emits the same structured timeline events (paced by `PACE` for a readable cadence, clearly labelled "Demo data" in the UI) but the stats are derived from a pre-canned report in the `DEMO_REPORTS` dict at the top of `app/main.py`; no API key, no network, no agents actually run. Competitor is resolved by substring match on name (`hubstaff` / `time doctor` / else `teramind`).
- **Live mode** — runs the real pipeline; agent/tool events carry real timings and tool I/O. Needs a key: either a server-side `GEMINI_API_KEY` **or** a **bring-your-own-key** (`api_key` in the `/api/analyze` body, used per-request, masked in any error, never stored/logged). The config UI reveals a key field when Demo is toggled off; the public Cloud Run deploy ships **no** key (demo-only). Results screen has a **"What just happened"** context view (`#view-about`) explaining the workflow + the ActivTrak org framing.

If you change the `CompetitorReport` schema, you must also update the hand-written `DEMO_REPORTS` entries to match, or demo mode will render inconsistently with live mode.

### Frontend
`app/static/` is plain HTML/CSS/vanilla JS (no framework, no build; light "SaaS" design system in `css/style.css` keyed off CSS variables). Mounted at `/` via `StaticFiles`. It's a single page with **three view states** swapped by `app.js`: config → run timeline → results. The three preset competitors (Teramind/Hubstaff/Time Doctor) with their mock URLs and claims are hardcoded in `app/static/js/app.js`.

**Source grounding is computed client-side, for real.** Each results "gap card" links to a source line via `groundGap()` in `app.js`: it anchors on the matching `preliminary_gaps[].doc_snippet` (the real evidence the `compare_claims_to_docs` MCP tool extracted — matched to the gap by overlap with its `technical_reality`, NOT the marketing-claim keyword, since several claims can share one), then picks the best `raw_doc` line by IDF- and number-weighted token overlap, and highlights it — no hardcoded citations. Works for any report (demo or live) as long as `raw_doc`/`preliminary_gaps` are present, so live mode needs no extra backend grounding.

## Gotchas

- **Always run from the repo root.** `app.main` mounts static files with the relative path `app/static`, imports modules as `app.*`, and spawns the MCP server with `-m app.mcp_server`. Running from elsewhere breaks all three.
- Not a git repository.
- Adding a new competitor requires edits in three places: `MOCK_DOCUMENTS` (`mcp_server.py`), `DEMO_REPORTS` (`main.py`), and the presets in `app/static/js/app.js`.
- The user's company is **ActivTrak** (`ActivTrak.com`) — set in `app/static/index.html` (own-domain default), `app/agents/analysis.py` (positioning prompt), and the `DEMO_REPORTS` battle-card copy in `app/main.py`. The owner amended the charter's original "Cmoconfessions" sanitization (`01_MISSION_CHARTER.md` §5) to use the real name. Still: only **public** competitor docs or mocks — no proprietary/internal data anywhere.
