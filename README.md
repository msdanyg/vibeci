# VibeCI — Competitive Intelligence Agent

> **AI Agents: Intensive Vibe Coding Capstone Project** | Track: *Agents for Business* | Deadline: July 6, 2026

[![Python](https://img.shields.io/badge/Python-3.11-blue.svg)](https://python.org)
[![Antigravity SDK](https://img.shields.io/badge/Google-Antigravity%20SDK-orange.svg)](https://pypi.org/project/google-antigravity/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-green.svg)](https://fastapi.tiangolo.com)
[![Cloud Run](https://img.shields.io/badge/Deploy-Cloud%20Run-blue.svg)](https://cloud.google.com/run)
[![License: CC-BY 4.0](https://img.shields.io/badge/License-CC--BY%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by/4.0/)

**🔗 Live demo:** **[vibeci-107532323288.us-central1.run.app](https://vibeci-107532323288.us-central1.run.app)** — runs in Demo mode, no key needed. Pick a competitor → Run analysis → click a citation to jump to the source line.

![VibeCI walkthrough — config → the five-agent pipeline → a battle card with every claim grounded to a source line → "what just happened" context](assets/demo.gif)

---

## 🎯 The Problem

Existing competitive-intelligence tools are **programmatic, not agentic**. They detect *that* a competitor's web page changed, then hand a diff to a Product Marketing Manager to interpret. They lack the context to understand *what the change means*. They do not read technical documentation, do not compare claimed capabilities against documented reality, and produce outputs that are stale on arrival.

A sales rep facing a Teramind objection needs to know that "real-time session monitoring" actually has a **2–5 minute upload lag** — a fact buried in their developer docs that no existing battle card surfaces.

## 💡 The Solution

**VibeCI** is a deployable, multi-agent system that:

1. **Reads** a competitor's technical documentation (API docs, KBs, developer portals — live or preloaded)
2. **Extracts** what their product *actually does* per use case
3. **Contrasts** documented reality against their marketing claims *and* your positioning
4. **Delivers** a structured, account-ready battle card — and **grounds every finding to a clickable source line** in the competitor's own docs

> **The Technical Analysis Agent is the star.** Discovery/monitoring is commodity. The defensible, impressive capability is reading API docs and surfacing — *provably* — the gap between marketing claims and documented reality.

---

## ✨ What makes the demo credible

The UI is built so a viewer can *trust* the output, not just read it:

- **Strategy-directed, not generic.** Before reading the competitor, a **Strategy / Research-Planner agent** turns *your* business context — messaging pillars, product roadmap, and solution map / ICP (with mocked connectors to Confluence / Productboard / Salesforce) — into a **research brief**: which lenses to scrutinise, who to frame the findings for, and which pillars to anchor the battle card in. Every gap is then tagged with the lens it answers. This is competitive intelligence *directed by your strategy*, not generic doc-diffing.
- **Real, clickable source grounding — measured and gated.** Every gap card carries a "View source ↗" citation. Clicking it scrolls the competitor's ingested documentation to — and highlights — the *exact line* that contradicts the marketing claim. The grounding is computed from the real documentation text (anchored on the evidence the MCP pre-screen tool extracted), **not hardcoded**. Each gap also gets a **grounding-confidence score** (0–100%, how strongly the doc backs it) shown right on the card — and an **eval** (`python -m eval.grounding_eval`, also a pytest gate) runs the real pipeline and *fails CI* if any finding stops grounding above threshold. The "Grounded" stat is earned, not asserted.
- **An honest agent run timeline.** Instead of a fake "hacker terminal," the run view shows the five agents executing in sequence, each with its model, elapsed time, and the **real MCP tool calls** it made (arguments in, structured result out).
- **Two clearly-signposted layers.** The product value ("the findings" — claim-vs-reality gap cards) is visually separated from the machinery ("under the hood" — the agent pipeline, the source document, the schema-validated JSON), so the engineering is legible without drowning the value.
- **Light, SaaS-grade design.** A calm, credible product surface where the only loud thing on the page is the claim-vs-reality gap.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     User (Browser, SPA)                     │
│  Config → Run timeline → Results, swapped client-side        │
│  Inputs: your positioning · competitor · doc URL · claims    │
└───────────────────────┬─────────────────────────────────────┘
                        │  POST /api/analyze  →  job_id
                        │  GET  /api/stream/{job_id}  (SSE)
                        ▼
┌─────────────────────────────────────────────────────────────┐
│              FastAPI Backend (Cloud Run)                     │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │   Multi-agent pipeline (google.antigravity SDK)      │   │
│  │                                                     │   │
│  │   Discovery ──▶ Technical Analysis ★ ──▶ Synthesis  │   │
│  │      │                                      │       │   │
│  │      │            ┌─────────────────────────▼─────┐ │   │
│  │      └──MCP──▶     │      Fact-Checking / QC       │ │   │
│  │                   └───────────────────────────────┘ │   │
│  │                                                     │   │
│  │  ┌──────────────────────────────────────────────┐   │   │
│  │  │        MCP Server (ci-doc-tools, stdio)       │   │   │
│  │  │  • fetch_competitor_docs                      │   │   │
│  │  │  • compare_claims_to_docs                     │   │   │
│  │  └──────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  Emits a structured SSE timeline (agent / tool / doc /      │
│  completed events) → the browser renders it live.           │
└─────────────────────────────────────────────────────────────┘
```

**SDK note:** the agents are built on the **`google.antigravity`** SDK (`from google.antigravity import Agent, LocalAgentConfig`), all targeting `gemini-2.0-flash`. Orchestration is explicit, sequential `await`s in `app/main.py` (not SDK-driven handoff), which is what lets the backend emit a clean, honest event timeline.

### Agent Descriptions

| Agent | Role | Reasoning |
|---|---|---|
| **Strategy / Research-Planner** | Reads your messaging pillars, roadmap & ICP → a research brief (prioritized lenses · who to frame for · which pillars) that steers the rest of the pipeline | `high` |
| **Discovery Agent** | Ingests competitor documentation via MCP tools; fetches live URLs or falls back to preloaded specs | `low` |
| **Technical Analysis Agent ★** | Reads raw specs, extracts real capabilities, contrasts against marketing claims and user positioning — prioritizing the brief's lenses | `high` |
| **Synthesis Agent** | Formats analysis into structured, Pydantic-validated JSON: battle cards, gap matrices, objection handlers — anchored in your pillars | `medium` |
| **Fact-Checking / QC Agent** | Grounds every claim back to the source documentation; removes hallucinations; re-validates the schema | `high` |

> All agents run `gemini-2.0-flash`, specialized by **reasoning effort** (`ThinkingLevel`), tools, and structured-output schema.

### MCP Server Tools

`app/mcp_server.py` exposes two tools over stdio (`FastMCP`):

| Tool | Description |
|---|---|
| `fetch_competitor_docs` | Fetches technical documentation from a URL (live HTTP GET, with mock fallback) |
| `compare_claims_to_docs` | Keyword-level pre-screen of marketing claims vs. documentation — extracts the doc snippets that contradict each claim (these become the grounding anchors) |

---

## 📊 Output Schema

Every run produces a validated `CompetitorReport` (Pydantic):

```json
{
  "competitor_name": "Teramind",
  "key_takeaways": ["..."],
  "gaps": [
    {
      "marketing_claim": "Real-time session monitoring with zero-latency",
      "technical_reality": "Screenshots packed into 5MB chunks, 2-5 min upload lag",
      "severity": "High Gaps",
      "sales_impact": "Pitch against the 'real-time' claim..."
    }
  ],
  "battle_card": {
    "elevator_pitch": "...",
    "strengths": ["..."],
    "weaknesses": ["..."],
    "objection_handling": [
      { "competitor_objection": "...", "our_response": "..." }
    ]
  },
  "sales_landmines": ["Ask: '...'"]
}
```

The response also carries `raw_doc` (the ingested source text) and `preliminary_gaps` (the MCP pre-screen hits), which power the client-side source grounding.

---

## 🚦 Two execution modes

| Mode | What runs | API key |
|---|---|---|
| **Demo** (default, the canonical showcase) | The full UI and SSE timeline render from pre-canned, schema-accurate reports. No network, deterministic, instant. | **None** |
| **Live** | The real five-agent Gemini pipeline ingests docs and generates the report end-to-end. | A **quota-enabled** `GEMINI_API_KEY` |

> Demo mode is the showcase: it needs no key, never rate-limits, and is reproducible for judging and portfolio review. Live mode is fully wired and authenticates/fetches/calls Gemini for real — it just needs a Google AI project with available `gemini-2.0-flash` quota (the free tier may be `0`; enable billing or use a quota-enabled key). If a live run hits a quota or key error, the UI surfaces a clean, actionable message and offers a one-click fallback to Demo mode.

---

## ✅ Course Concepts Demonstrated

| Concept | Where | Status |
|---|---|---|
| **Multi-agent system** | `app/agents/` — 5 agents orchestrated via `google.antigravity`, surfaced in a live run timeline | ✅ Built |
| **MCP Server** | `app/mcp_server.py` — `fetch_competitor_docs` + `compare_claims_to_docs`, with real tool-call I/O shown in the UI | ✅ Built |
| **Source grounding** | Every claim links to the exact line in the competitor's docs; computed for real (`app/grounding.py`) | ✅ Built |
| **Grounding-confidence eval** | Per-gap confidence score, surfaced in-app and **gated** by `eval/grounding_eval.py` + pytest | ✅ Built |
| **Structured output** | Pydantic `CompetitorReport` schema, validated and viewable in-app | ✅ Built |
| **Deployability** | `Dockerfile` + Cloud Run config (see below) | ✅ Built |
| **Antigravity** | Agentic build process shown in video | 🎯 Target |

---

## 🚀 Setup & Running Locally

### Prerequisites

- Python 3.11+
- (Optional) A [Gemini API key](https://aistudio.google.com/) with quota — **only** for Live mode; Demo mode needs none

### 1. Install

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure (optional — Live mode only)

```bash
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY (for Live mode)
```

### 3. Run — **from the repo root**

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

Open [http://localhost:8080](http://localhost:8080). Demo mode is on by default, so it works immediately with no key.

> ⚠️ Always run from the repo root — the app mounts `app/static`, imports modules as `app.*`, and spawns the MCP server with `-m app.mcp_server`, all relative to the working directory.

---

## 🧪 Tests

A `pytest` suite covers the deterministic core — the MCP document tools (live-fetch with mock fallback, the claims-vs-docs pre-screen), the full demo pipeline (incl. the structured SSE event timeline the frontend and notebook depend on), and a **grounding-confidence gate** that fails if any finding stops grounding to its source line above threshold:

```bash
pip install -r requirements-dev.txt
pytest                       # run from the repo root

# The grounding eval also runs standalone — prints a per-gap confidence report:
python -m eval.grounding_eval
```

```
  VibeCI · GROUNDING-CONFIDENCE EVAL
  Teramind       avg 100%   min 100%   [PASS]
  Hubstaff       avg  79%   min  58%   [PASS]
  Time Doctor    avg  85%   min  56%   [PASS]
  CORPUS: 8/8 gaps grounded ≥ 45%  ·  avg confidence 89%  ·  min 56%
  RESULT: ✓ PASS — grounding holds across the corpus
```

---

## 🐳 Docker Deployment (Cloud Run)

### Build & run locally

```bash
docker build -t vibeci .
docker run -p 8080:8080 -e GEMINI_API_KEY=your_key_here vibeci   # key optional; Demo mode needs none
```

### Deploy to Google Cloud Run (demo-only — no key shipped)

```bash
# one-time (your account / project; billing enabled)
./gcloud.sh auth login
./gcloud.sh config set project YOUR_PROJECT_ID

# deploy — builds from the Dockerfile via Cloud Build, then deploys
./deploy.sh
#  ≡ gcloud run deploy vibeci --source . --region us-central1 \
#        --allow-unauthenticated --max-instances 1
```

> **Demo-only by design.** No `GEMINI_API_KEY` is set on the service, so the public instance runs Demo mode (Live shows a graceful "needs a key" message). `.gcloudignore` keeps `.env` out of the build upload entirely. To enable Live, redeploy appending `--set-env-vars GEMINI_API_KEY=<quota-enabled-key>`.
>
> **Single instance.** Job state is in-memory, so the deploy pins `--max-instances 1` — the SSE stream must hit the same process that ran the job (don't add `--workers`).

---

## 📁 Project Structure

```
.
├── app/
│   ├── main.py              # FastAPI backend — job queue, SSE timeline, pipeline orchestration
│   ├── grounding.py         # Source grounding + grounding-confidence score (server source of truth)
│   ├── mcp_server.py        # MCP server: fetch_competitor_docs + compare_claims_to_docs
│   ├── agents/
│   │   ├── config.py        # Shared model config + the five agent personas
│   │   ├── strategy.py      # Strategy Agent — reads business context → Research Brief
│   │   ├── discovery.py     # Discovery Agent — uses the MCP server over stdio
│   │   ├── analysis.py      # Technical Analysis Agent ★
│   │   ├── synthesis.py     # Synthesis Agent — Pydantic structured output
│   │   └── checking.py      # Fact-Checking / QC Agent
│   └── static/              # Frontend — vanilla HTML/CSS/JS, no framework, no build
│       ├── index.html       # 5 views: config → run → results → landscape → about
│       ├── css/style.css    # Light, SaaS-grade design system
│       └── js/app.js        # SSE client, run timeline, results + real source grounding
├── eval/
│   └── grounding_eval.py    # Grounding-confidence eval — runs the real pipeline, gates on the score
├── tests/                   # pytest — MCP tools, demo pipeline/SSE contract, grounding gate
├── Dockerfile
├── requirements.txt
├── .env.example
└── README.md
```

---

## 🔒 Security & Honesty

- **No API keys in code.** All secrets are passed via environment variables (`.env` locally, `--set-env-vars` on Cloud Run).
- **SSRF-guarded doc fetch.** The live fetch only follows public `http(s)` URLs; loopback, private, link-local (incl. the `169.254.169.254` cloud-metadata endpoint), and reserved hosts are rejected and fall back to mock data.
- **Source grounding is real.** Findings trace to the actual ingested documentation; the Fact-Checking agent removes claims not backed by the docs, and the UI lets anyone verify each claim against its source line.
- **Demo mode is labelled as demo.** Pre-canned data is clearly marked "Demo data" in the UI — never presented as a live run.
- **No proprietary data.** This build uses sanitized, publicly-available competitor documentation or high-fidelity mocks. No internal company data is included.

---

## 🗺️ Extension Paths (Designed, Not Built)

Per the project charter, these are architecture-designed but deliberately deferred:

- **Change-tracking agent** — diff competitor docs over time; alert on updates
- **Strategy agent** — recommend positioning moves based on gap trends
- **Account differentiation agent** — map gaps to specific deal opportunities
- **Live CRM integration** — push battle cards into Salesforce (currently illustrative)
- **Live KB integration** — connect the user's internal knowledge base (currently mocked via pasted positioning)

---

## 📜 License

CC-BY 4.0 — See [LICENSE](LICENSE) for details.

Built for the [Kaggle AI Agents: Intensive Vibe Coding Capstone Project](https://www.kaggle.com/competitions/vibecoding-agents-capstone-project).
