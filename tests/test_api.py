"""Integration tests for the FastAPI app (app/main.py).

Covers the HTTP contract (static serving, 404s, the live-mode key gate) and the
full demo pipeline — including the structured SSE event sequence that the
frontend run-timeline and the Kaggle notebook both depend on.

Run from the repo root: `pytest`.
"""
import asyncio

from starlette.testclient import TestClient

import app.main as main
from app.main import app, AnalyzeRequest, execute_workflow, jobs, queues

client = TestClient(app)


# --------------------------------------------------------------------------- #
# HTTP contract (no pipeline)
# --------------------------------------------------------------------------- #
def test_index_is_served():
    r = client.get("/")
    assert r.status_code == 200
    assert "VibeCI" in r.text


def test_unknown_job_returns_404():
    assert client.get("/api/job/does-not-exist").status_code == 404


def test_unknown_stream_returns_404():
    assert client.get("/api/stream/does-not-exist").status_code == 404


def test_live_mode_requires_api_key(monkeypatch):
    # Demo mode needs no key; live mode must reject when no key is available at all.
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    r = client.post("/api/analyze", json={
        "competitor_name": "Teramind",
        "marketing_claims": "x",
        "own_positioning": "y",
        "demo_mode": False,
    })
    assert r.status_code == 400
    assert "key" in r.json()["detail"].lower()


def test_live_mode_accepts_bring_your_own_key(monkeypatch):
    # With no server key, a caller-supplied api_key passes the gate (the pipeline
    # itself is stubbed here so no real network call is made).
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    async def _noop(job_id, request):
        return
    monkeypatch.setattr(main, "execute_workflow", _noop)

    r = client.post("/api/analyze", json={
        "competitor_name": "Teramind",
        "marketing_claims": "x",
        "own_positioning": "y",
        "demo_mode": False,
        "api_key": "byok-test-key",
    })
    assert r.status_code == 200
    assert "job_id" in r.json()


def test_landscape_returns_field_matrix():
    r = client.post("/api/landscape", json={"demo_mode": True, "icp": "IT leaders at regulated firms"})
    assert r.status_code == 200
    L = r.json()
    assert L["competitors"] and L["dimensions"]
    assert all(c in L["matrix"] for c in L["competitors"])           # every competitor scored
    assert all(d["name"] in L["matrix"][L["competitors"][0]] for d in L["dimensions"])
    assert "IT leaders" in L["field_brief"]["icp"]                    # field brief echoes the caller's ICP


def test_demo_mode_starts_a_job_without_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    r = client.post("/api/analyze", json={
        "competitor_name": "Teramind",
        "doc_url": "mock://x",
        "marketing_claims": "Real-time, zero-latency, lightweight.",
        "own_positioning": "privacy-first",
        "demo_mode": True,
    })
    assert r.status_code == 200
    assert "job_id" in r.json()


# --------------------------------------------------------------------------- #
# The demo pipeline + structured event timeline
# --------------------------------------------------------------------------- #
async def test_demo_workflow_emits_full_structured_timeline(monkeypatch):
    # Make the demo pacing instant so the test is fast.
    async def _instant(*a, **k):
        return
    monkeypatch.setattr(main.asyncio, "sleep", _instant)

    job_id = "pytest-demo-job"
    jobs[job_id] = {"status": "running", "events": [], "result": None, "error": None}
    queues[job_id] = asyncio.Queue()

    req = AnalyzeRequest(
        competitor_name="Hubstaff",
        doc_url="mock://x",
        marketing_claims="Seamless and accurate time tracking.",
        own_positioning="privacy-first",
        demo_mode=True,
    )
    await execute_workflow(job_id, req)

    # result shape
    assert jobs[job_id]["status"] == "completed"
    report = jobs[job_id]["result"]
    assert report["competitor_name"] == "Hubstaff"
    assert len(report["gaps"]) >= 1
    assert report["raw_doc"]
    assert isinstance(report["preliminary_gaps"], list)
    assert {"battle_card", "key_takeaways", "sales_landmines"} <= report.keys()

    events = jobs[job_id]["events"]
    types = [e["type"] for e in events]
    assert types[0] == "mode"
    assert types[-1] == "completed"
    assert "doc" in types  # source preview streamed

    # both MCP tools surfaced with their names
    tool_names = {e["name"] for e in events if e["type"] == "tool"}
    assert {"fetch_competitor_docs", "compare_claims_to_docs"} <= tool_names

    # all five agents reported a 'done' phase (incl. the Strategy planner)
    done_agents = {e["agent"] for e in events
                   if e["type"] == "agent" and e.get("phase") == "done"}
    assert done_agents == {"strategy", "discovery", "analysis", "synthesis", "checking"}

    # the Strategy agent emitted a research brief that steered the run
    assert any(e["type"] == "brief" for e in events)
    brief = report["research_brief"]
    assert brief["lenses"] and brief["icp"] and brief["pillars"]
    # every gap is tagged with the lens it answers
    assert all(g.get("lens") for g in report["gaps"])

    # cleanup module-level state
    jobs.pop(job_id, None)
    queues.pop(job_id, None)


async def test_demo_workflow_resolves_competitor_by_substring(monkeypatch):
    async def _instant(*a, **k):
        return
    monkeypatch.setattr(main.asyncio, "sleep", _instant)

    job_id = "pytest-td-job"
    jobs[job_id] = {"status": "running", "events": [], "result": None, "error": None}
    queues[job_id] = asyncio.Queue()

    req = AnalyzeRequest(
        competitor_name="Time Doctor",
        marketing_claims="Real-time tracking.",
        own_positioning="privacy-first",
        demo_mode=True,
    )
    await execute_workflow(job_id, req)

    report = jobs[job_id]["result"]
    assert report["competitor_name"] == "Time Doctor"
    # Time Doctor's preloaded report has 3 gaps
    assert len(report["gaps"]) == 3

    jobs.pop(job_id, None)
    queues.pop(job_id, None)
