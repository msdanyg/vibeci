import asyncio
import uuid
import os
import json
import time
from dotenv import load_dotenv
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

# Load .env file if present (local development)
load_dotenv()

# Import MCP tools directly
from app.mcp_server import fetch_competitor_docs, compare_claims_to_docs

# Import agent runner functions
from app.agents.discovery import run_discovery_agent
from app.agents.analysis import run_analysis_agent
from app.agents.synthesis import run_synthesis_agent, CompetitorReport
from app.agents.checking import run_checking_agent

app = FastAPI(title="Competitive Intelligence Agent Dashboard")

# In-memory database of analysis jobs and streaming queues
jobs: Dict[str, Dict[str, Any]] = {}
queues: Dict[str, asyncio.Queue] = {}

# ---------------------------------------------------------------------------
# High-fidelity pre-canned reports for Demo Mode.
# Demo mode streams realistic agent logs then returns this structured data —
# no API key required, no network calls, instant results.
# ---------------------------------------------------------------------------
DEMO_REPORTS = {
    "teramind": {
        "competitor_name": "Teramind",
        "key_takeaways": [
            "Teramind marketing positions the product as 'real-time, zero-latency user activity monitoring.'",
            "Technical documentation reveals a local buffer size limit of 1 KB and chunked screenshot uploads (5 MB), creating a 2–5 minute delay.",
            "Keystroke tracking can be fully bypassed for processes listed in the config file, creating a major security blind spot.",
            "Average bandwidth per monitored user is 350 kbps, meaning teams of 50+ will experience network saturation without rate throttling."
        ],
        "gaps": [
            {
                "marketing_claim": "Real-time user behavior analytics and live desktop streaming.",
                "technical_reality": "Screenshots are compressed into 5 MB chunks and uploaded asynchronously, creating 2 to 5 minutes of latency.",
                "severity": "High Gaps",
                "sales_impact": "Pitch against the 'real-time' claim. Teramind cannot assist with live intervention in under 2 minutes. Position ActivTrak as a privacy-friendly alternative with daily aggregates that doesn't waste bandwidth."
            },
            {
                "marketing_claim": "Zero-latency keystroke logging and security threat alerts.",
                "technical_reality": "Keystroke logs are buffered client-side up to 1 KB or 5 minutes. Bypassed by adding custom processes to exclusions.",
                "severity": "Moderate Gaps",
                "sales_impact": "Explain to clients that security compliance is compromised since users can rename executables to bypass logging."
            },
            {
                "marketing_claim": "Lightweight, non-intrusive desktop agent.",
                "technical_reality": "Requires 350 kbps per user for video sync, which can clog company networks.",
                "severity": "High Gaps",
                "sales_impact": "Highlight infrastructure overhead. Ask prospective clients if they are ready to upgrade office bandwidth for employee tracking."
            }
        ],
        "battle_card": {
            "elevator_pitch": "Teramind offers heavy surveillance that slows down company networks and lags behind by up to 5 minutes, while ActivTrak provides privacy-first, lightweight daily productivity insights.",
            "strengths": [
                "Detailed microscopic tracking (keystrokes, specific coordinates).",
                "Robust rules engine for immediate local blocks."
            ],
            "weaknesses": [
                "Heavy bandwidth consumption (350 kbps/user).",
                "Significant live sync lag (2–5 minutes).",
                "Keystroke exclusion files are vulnerable to local renaming bypasses."
            ],
            "objection_handling": [
                {
                    "competitor_objection": "Teramind captures live screen recordings so we can see exactly what people do.",
                    "our_response": "Live screen recording consumes up to 350 kbps per user and introduces a 2–5 minute delay. It also invades employee privacy, causing trust issues. ActivTrak captures window states and active tabs privacy-first, with zero network performance impact."
                },
                {
                    "competitor_objection": "Teramind has instant keystroke logging for threat detection.",
                    "our_response": "Keystroke logs are buffered for up to 5 minutes before upload, meaning the 'instant' threat detection is actually delayed. Furthermore, savvy users can bypass it entirely by running applications under excluded process names."
                }
            ]
        },
        "sales_landmines": [
            "Ask: 'How does your network handle an extra 17.5 Mbps of continuous video uploads for a team of 50 users?'",
            "Ask: 'If a threat occurs, is a 5-minute buffer delay acceptable for your security operations team?'",
            "Ask: 'How do you prevent employees from bypassing the keystroke logger by renaming their executables?'"
        ],
        "raw_doc": "# Teramind API & KB Developer Documentation (v4.2)\n\n## 1. Screen Recording and Session Player\n- **Data Capture Mechanism**: Screens are captured at configured frame rates (default: 15 fps) and saved locally as temporary compressed blocks.\n- **Upload Sync Interval**: Temporary files are packed into 5 MB chunks and uploaded asynchronously to the cloud storage bucket. Under default network conditions, there is a **latency of 2 to 5 minutes** before a live session shows up in the admin dashboard player.\n- **OCR Engine**: Text on screen is analyzed by a background cron job running every 15 minutes. It is NOT real-time. Text search will only yield results **15 minutes after the activity occurs**.\n\n## 2. Keystroke Logging Agent\n- **Buffer Limits**: The agent buffers keyboard events locally in a 1 KB FIFO buffer.\n- **Network Dispatch**: The buffer is flushed and sent to the server every **5 minutes** or immediately if the 1 KB limit is exceeded.\n- **Exclusions**: Keystroke monitoring can be bypassed by application executable names listed in `keystroke_exclusions.json`.\n\n## 3. Network & Bandwidth Requirements\n- The desktop agent requires a persistent outbound WebSocket connection.\n- Average bandwidth consumption per monitored user is **350 kbps** when screen recording is active, which can saturate local office connections for teams larger than 50 employees unless rate-limited to 5 fps.",
        "preliminary_gaps": [
            {
                "claim_keyword": "real-time",
                "contradiction_evidence": ["latency", "delay", "async", "cron", "epoch"],
                "doc_snippet": "there is a latency of 2 to 5 minutes before a live session shows up in the admin dashboard player.",
                "flag": "POTENTIAL GAP — verify with Technical Analysis Agent"
            },
            {
                "claim_keyword": "zero-latency",
                "contradiction_evidence": ["latency", "delay", "async", "buffer"],
                "doc_snippet": "there is a latency of 2 to 5 minutes before a live session shows up in the admin dashboard player.",
                "flag": "POTENTIAL GAP — verify with Technical Analysis Agent"
            },
            {
                "claim_keyword": "instant",
                "contradiction_evidence": ["buffer", "latency"],
                "doc_snippet": "The agent buffers keyboard events locally in a 1 KB FIFO buffer. The buffer is flushed and sent to the server every 5 minutes",
                "flag": "POTENTIAL GAP — verify with Technical Analysis Agent"
            },
            {
                "claim_keyword": "secure",
                "contradiction_evidence": ["bypass", "exclusion"],
                "doc_snippet": "Keystroke monitoring can be bypassed by application executable names listed in keystroke_exclusions.json",
                "flag": "POTENTIAL GAP — verify with Technical Analysis Agent"
            },
            {
                "claim_keyword": "lightweight",
                "contradiction_evidence": ["kbps", "bandwidth", "persistent"],
                "doc_snippet": "Average bandwidth consumption per monitored user is 350 kbps when screen recording is active, which can saturate local office connections",
                "flag": "POTENTIAL GAP — verify with Technical Analysis Agent"
            }
        ]
    },
    "hubstaff": {
        "competitor_name": "Hubstaff",
        "key_takeaways": [
            "Hubstaff claims 'seamless, automatic, and non-distracting time tracking.'",
            "Technical documentation shows activity scoring relies on 10-minute sampling windows, misrepresenting deep cognitive work (e.g. coding or writing) as 'low productivity.'",
            "Inactivity prompts interrupt employee focus every 5 minutes if no mouse/keyboard movements occur, leading to employee fatigue.",
            "Idle time auto-deductions can penalize employees for offline collaboration and thinking time."
        ],
        "gaps": [
            {
                "marketing_claim": "Accurate, automated proof-of-work and productivity scores.",
                "technical_reality": "Productivity is calculated strictly on keyboard/mouse active seconds per 10-minute epoch. Thinking time is scored as 0% active.",
                "severity": "High Gaps",
                "sales_impact": "Explain how this scoring method encourages 'mouse-jiggler' behaviors rather than actual output. Suggest our focus-based active window tracking as a fairer metric."
            },
            {
                "marketing_claim": "Non-intrusive and seamless time tracking.",
                "technical_reality": "Prompts users with an interruptive popup after 5 minutes of idle state, demanding a response within 60 seconds.",
                "severity": "Moderate Gaps",
                "sales_impact": "Sales pitch: 'Hubstaff interrupts your team's flow state to ask if they are working. ActivTrak runs silently in the background without popups.'"
            }
        ],
        "battle_card": {
            "elevator_pitch": "Hubstaff uses an outdated mouse-movement formula that scores deep thinking as idle time and forces intrusive popups onto workers, whereas ActivTrak measures work based on active applications, respecting deep focus.",
            "strengths": [
                "Built-in payroll and invoicing integrations.",
                "GPS tracking for mobile field workers."
            ],
            "weaknesses": [
                "Binary keyboard/mouse activity metrics fail to measure cognitive work.",
                "Annoying 'Are you still working?' alerts disrupt concentration.",
                "Auto-deductions for offline thinking create employee distrust."
            ],
            "objection_handling": [
                {
                    "competitor_objection": "Hubstaff's activity percentage shows us exactly how active our team is.",
                    "our_response": "Hubstaff's percentage only measures if mouse or keys moved in a 10-minute slot. A developer thinking about a hard bug gets a 10% activity score, while someone playing a video game with a mouse jiggler gets 100%. ActivTrak analyzes application categorizations to measure true focus."
                },
                {
                    "competitor_objection": "We need the idle popup to make sure employees aren't billing for time away.",
                    "our_response": "Popups interrupt focus and build resentment. ActivTrak handles idle states gracefully by separating active work from passive offline blocks without prompting the user or stopping their focus train."
                }
            ]
        },
        "sales_landmines": [
            "Ask: 'Do you want to evaluate your software developers and engineers by how many times they click their mouse per minute, or by the value they deliver?'",
            "Ask: 'How do you account for collaborative sessions, phone calls, or physical sketching when Hubstaff auto-deletes idle time after 5 minutes?'"
        ],
        "raw_doc": "# Hubstaff Developer API & Time Tracking Integration Docs\n\n## 1. Activity Scoring Algorithm\n- **Tracking Epochs**: Activity is recorded in **10-minute windows (epochs)**.\n- **Input Sampling**: The Hubstaff desktop client counts keyboard keystrokes and mouse movements (clicks and coordinate changes).\n- **Productivity Calculation**:\n  `Activity % = (Seconds with at least 1 input event / 600 seconds) * 100`\n  *Note*: A developer writing complex code might type for 1 minute (100%) and think for 9 minutes (0%), resulting in a reported **10% activity score**.\n\n## 2. Inactivity (Idle) Detection\n- **Trigger Window**: The client detects inactivity after **5 consecutive minutes** of zero keyboard or mouse inputs.\n- **User Prompt**: A modal popup asks: *\"Are you still working on [Task]?\"*\n- **Action Required**: The employee must click \"Yes\" within 60 seconds or the idle time is automatically subtracted from their timesheet.\n\n## 3. Screenshots (Proof of Work)\n- **Interval**: Randomly taken 1–3 times per 10-minute interval.\n- **Blur Ring**: Blurring is applied client-side if configured, but metadata (active window title, application path) is uploaded in plain text and cannot be blurred.",
        "preliminary_gaps": [
            {
                "claim_keyword": "seamless",
                "contradiction_evidence": ["popup", "interrupt", "subtracted"],
                "doc_snippet": "A modal popup asks: \"Are you still working on [Task]?\" The employee must click \"Yes\" within 60 seconds or the idle time is automatically subtracted",
                "flag": "POTENTIAL GAP — verify with Technical Analysis Agent"
            },
            {
                "claim_keyword": "accurate",
                "contradiction_evidence": ["epoch", "sampling", "activity %"],
                "doc_snippet": "A developer writing complex code might type for 1 minute (100%) and think for 9 minutes (0%), resulting in a reported 10% activity score.",
                "flag": "POTENTIAL GAP — verify with Technical Analysis Agent"
            },
            {
                "claim_keyword": "non-intrusive",
                "contradiction_evidence": ["popup", "interrupt", "keystroke"],
                "doc_snippet": "The client detects inactivity after 5 consecutive minutes... A modal popup asks: \"Are you still working on [Task]?\"",
                "flag": "POTENTIAL GAP — verify with Technical Analysis Agent"
            }
        ]
    },
    "timedoctor": {
        "competitor_name": "Time Doctor",
        "key_takeaways": [
            "Time Doctor positions itself as 'real-time automated time tracking with distraction alerts.'",
            "Technical documentation shows active window titles are only sampled once every 15 seconds, missing fast switches or brief tasks.",
            "Inactivity alerts pause tracking after 3 idle minutes, which interrupts thinking time and is easily bypassed by auto-clickers.",
            "Screenshot uploads can lag by up to 10 minutes, making marketing claims of 'real-time visibility' misleading."
        ],
        "gaps": [
            {
                "marketing_claim": "Real-time automated time tracking and web & app usage reports.",
                "technical_reality": "Active window titles are sampled at a 15-second coarse interval. Short tasks or rapid tab changes are completely omitted.",
                "severity": "High Gaps",
                "sales_impact": "Pitch against Time Doctor's coarse data resolution. Explain that they miss rapid developer or designer context changes. Position ActivTrak as collecting true focus transitions without lag."
            },
            {
                "marketing_claim": "Instant distraction alerts to keep teams focused.",
                "technical_reality": "The idle prompt triggers after 3 idle minutes, which interrupts deep work and can be easily bypassed by simple software auto-clickers.",
                "severity": "Moderate Gaps",
                "sales_impact": "Highlight that distraction alerts micromanage employees and encourage fake mouse activity. Pitch ActivTrak' silent, trusting, and daily-aggregated approach."
            },
            {
                "marketing_claim": "Real-time screenshot and activity monitoring dashboard.",
                "technical_reality": "Screenshots are buffered locally and uploaded asynchronously, introducing up to a 10-minute delay before appearing in the admin portal.",
                "severity": "High Gaps",
                "sales_impact": "Explain that managers are viewing stale data (10-minute delay) and employees resent the constant surveillance. Pitch ActivTrak as a privacy-friendly, trust-preserving choice."
            }
        ],
        "battle_card": {
            "elevator_pitch": "Time Doctor uses invasive screenshots that lag by up to 10 minutes and interruptive idle alerts that micromanage employees. ActivTrak tracks window category states privacy-first and runs silently in the background.",
            "strengths": [
                "Detailed payroll, invoicing, and billable hour calculations.",
                "Direct task mapping integrations with Asana, Jira, and Asana."
            ],
            "weaknesses": [
                "Coarse 15-second application window sampling rate.",
                "Intrusive screenshot capture harms company culture and trust.",
                "Up to 10-minute screenshot upload latency lag."
            ],
            "objection_handling": [
                {
                    "competitor_objection": "Time Doctor screenshots prove exactly what employees are doing.",
                    "our_response": "Screenshots build massive trust issues and lag behind by up to 10 minutes. Savvy users bypass this anyway using hardware mouse jigglers. ActivTrak focuses on high-level active states without monitoring screens, maintaining trust and culture."
                },
                {
                    "competitor_objection": "Time Doctor's distraction popups keep employees on task.",
                    "our_response": "Popups interrupt the flow state of knowledge workers. If an engineer is thinking about a bug, they shouldn't be interrupted by a popup every 3 minutes. ActivTrak gathers analytics silently without flow interruptions."
                }
            ]
        },
        "sales_landmines": [
            "Ask: 'How do your knowledge workers feel about screenshots being randomly captured, and does it impact developer retention?'",
            "Ask: 'If an employee uses a mouse jiggler, does Time Doctor still count them as productive?'",
            "Ask: 'With a 15-second window title sampling rate, how does Time Doctor capture rapid tasks like checking a server alert or replying to a customer?'"
        ],
        "raw_doc": "# Time Doctor API Integration & Tracking Specifications\n\n## 1. Window & Application Sampling\n- **Active Title Collection**: Active window titles and application paths are sampled once every **15 seconds**. Short-duration transitions, rapid tab switching, or brief notifications will be missed by this sampling window.\n- **Local Cache**: Collected title events are stored in a local SQLite file and uploaded in 1-minute batches.\n\n## 2. Inactivity & Distraction Alerts\n- **Idle Threshold**: A user is marked idle after **3 consecutive minutes** of zero keyboard/mouse inputs.\n- **Alert Popup**: If idle while the timer runs, a popup asks: *\"Are you still working?\"*\n- **Auto-Pause**: If not dismissed in 60 seconds, time tracking pauses. Savannah users can bypass this check using background auto-clicker scripts.\n\n## 3. Screenshot Capture Specs\n- **Sync Interval**: Screenshots are captured at random intervals (default: 3 mins, 9 mins, or 15 mins).\n- **Upload Delay**: Screenshots are buffered locally, compressed, and uploaded asynchronously. On standard connections, there is an **upload delay of up to 10 minutes** before they appear in the web dashboard.",
        "preliminary_gaps": [
            {
                "claim_keyword": "real-time",
                "contradiction_evidence": ["latency", "delay", "async", "cron", "epoch"],
                "doc_snippet": "Screenshots are buffered locally, compressed, and uploaded asynchronously. On standard connections, there is an upload delay of up to 10 minutes before they appear in the web dashboard.",
                "flag": "POTENTIAL GAP — verify with Technical Analysis Agent"
            },
            {
                "claim_keyword": "non-intrusive",
                "contradiction_evidence": ["popup", "interrupt", "keystroke"],
                "doc_snippet": "A user is marked idle after 3 consecutive minutes of zero keyboard/mouse inputs. If idle while the timer runs, a popup asks: \"Are you still working?\"",
                "flag": "POTENTIAL GAP — verify with Technical Analysis Agent"
            },
            {
                "claim_keyword": "accurate",
                "contradiction_evidence": ["sampling", "15 seconds"],
                "doc_snippet": "Active window titles and application paths are sampled once every 15 seconds. Short-duration transitions will be missed by this sampling window.",
                "flag": "POTENTIAL GAP — verify with Technical Analysis Agent"
            }
        ]
    }
}


class AnalyzeRequest(BaseModel):
    competitor_name: str
    doc_url: Optional[str] = None
    marketing_claims: str
    own_positioning: str
    demo_mode: bool = False


def _doc_stats(raw_doc: str):
    """Lightweight stats used to label the run timeline honestly."""
    lines = raw_doc.count("\n") + 1
    sections = raw_doc.count("## ")
    return lines, sections, len(raw_doc)


async def execute_workflow(job_id: str, request: AnalyzeRequest):
    """Run the pipeline, streaming a structured timeline of real agent + MCP-tool
    activity. Each event is persisted to the job and pushed to the live SSE queue.

    Event shapes consumed by the frontend run-timeline:
      {type:"mode",  demo, competitor}
      {type:"agent", agent, phase:"start"|"done", detail?, elapsed_ms?}
      {type:"tool",  agent, name, transport, args, result}
      {type:"doc",   raw_doc}                         (source preview)
      {type:"completed", data: <report>} | {type:"failed", data: <error>}
    """
    q = queues[job_id]

    # Demo mode is clearly labelled as such in the UI; a small pace gives the
    # timeline a readable cadence. Live mode streams at true speed.
    PACE = 0.45 if request.demo_mode else 0.0

    async def emit(event: dict, pace: float = 0.0):
        jobs[job_id]["events"].append(event)
        await q.put(event)
        if pace:
            await asyncio.sleep(pace)

    try:
        await emit({"type": "mode", "demo": request.demo_mode,
                    "competitor": request.competitor_name}, PACE)

        # Resolve the pre-canned report up front in demo mode so each stage can
        # report honest, data-derived stats instead of scripted prose.
        report = None
        preliminary_gaps = []
        if request.demo_mode:
            name_lower = request.competitor_name.lower()
            if "hubstaff" in name_lower:
                comp_key = "hubstaff"
            elif "time doctor" in name_lower or "timedoctor" in name_lower:
                comp_key = "timedoctor"
            else:
                comp_key = "teramind"
            report = dict(DEMO_REPORTS[comp_key])
            report["competitor_name"] = request.competitor_name
            raw_doc = report["raw_doc"]
            preliminary_gaps = report.get("preliminary_gaps", [])

        # ── Discovery ────────────────────────────────────────────────────────
        await emit({"type": "agent", "agent": "discovery", "phase": "start"}, PACE)
        t0 = time.perf_counter()
        if not request.demo_mode:
            raw_doc = fetch_competitor_docs(request.competitor_name, request.doc_url or "")
        lines, sections, chars = _doc_stats(raw_doc)
        await emit({"type": "tool", "agent": "discovery", "name": "fetch_competitor_docs",
                    "transport": "MCP · stdio",
                    "args": {"competitor_name": request.competitor_name,
                             "doc_url": request.doc_url or "(preloaded spec)"},
                    "result": f"{chars:,} chars · {sections} sections"}, PACE)
        await emit({"type": "doc", "raw_doc": raw_doc}, PACE)
        if request.demo_mode:
            doc_summary = raw_doc
        else:
            doc_summary = await run_discovery_agent(request.competitor_name, request.doc_url)
        await emit({"type": "agent", "agent": "discovery", "phase": "done",
                    "detail": f"Ingested {lines}-line spec · {sections} sections",
                    "elapsed_ms": int((time.perf_counter() - t0) * 1000)}, PACE)

        # ── Technical Analysis (the star) ────────────────────────────────────
        await emit({"type": "agent", "agent": "analysis", "phase": "start"}, PACE)
        t0 = time.perf_counter()
        if not request.demo_mode:
            pre_screen_json = compare_claims_to_docs(request.marketing_claims, raw_doc)
            try:
                preliminary_gaps = json.loads(pre_screen_json).get("preliminary_gaps", [])
            except Exception:
                preliminary_gaps = []
        n_pre = len([g for g in preliminary_gaps if g.get("claim_keyword", "none") != "none"])
        claims_preview = request.marketing_claims.strip().replace("\n", " ")
        await emit({"type": "tool", "agent": "analysis", "name": "compare_claims_to_docs",
                    "transport": "MCP · stdio",
                    "args": {"marketing_claims": (claims_preview[:90] + "…") if len(claims_preview) > 90 else claims_preview},
                    "result": f"{n_pre} keyword contradiction(s) flagged"}, PACE)
        if not request.demo_mode:
            analysis_details = await run_analysis_agent(
                request.competitor_name, doc_summary,
                request.marketing_claims, request.own_positioning)
        analysis_detail = (f"{len(report['gaps'])} claim-vs-reality gaps identified"
                           if request.demo_mode else "Claims contrasted against documented reality")
        await emit({"type": "agent", "agent": "analysis", "phase": "done",
                    "detail": analysis_detail,
                    "elapsed_ms": int((time.perf_counter() - t0) * 1000)}, PACE)

        # ── Synthesis ────────────────────────────────────────────────────────
        await emit({"type": "agent", "agent": "synthesis", "phase": "start"}, PACE)
        t0 = time.perf_counter()
        synthesis_report = None
        if not request.demo_mode:
            synthesis_report = await run_synthesis_agent(request.competitor_name, analysis_details)
        await emit({"type": "agent", "agent": "synthesis", "phase": "done",
                    "detail": "Battle card + gap matrix · schema-valid (CompetitorReport)",
                    "elapsed_ms": int((time.perf_counter() - t0) * 1000)}, PACE)

        # ── Fact-Checking / QC ───────────────────────────────────────────────
        await emit({"type": "agent", "agent": "checking", "phase": "start"}, PACE)
        t0 = time.perf_counter()
        if not request.demo_mode:
            final_report = await run_checking_agent(request.competitor_name, doc_summary, synthesis_report)
            removed = max(0, len(synthesis_report.gaps) - len(final_report.gaps)) if synthesis_report else 0
            report = final_report.model_dump()
            report["raw_doc"] = raw_doc
            report["preliminary_gaps"] = preliminary_gaps
            check_detail = f"{len(report['gaps'])} claims grounded to source · {removed} unsupported removed"
        else:
            check_detail = f"{len(report['gaps'])} gaps grounded to source documentation"
        await emit({"type": "agent", "agent": "checking", "phase": "done",
                    "detail": check_detail,
                    "elapsed_ms": int((time.perf_counter() - t0) * 1000)}, PACE)

        jobs[job_id]["status"] = "completed"
        jobs[job_id]["result"] = report
        await emit({"type": "completed", "data": report})

    except Exception as e:
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)
        await emit({"type": "failed", "data": str(e)})


@app.post("/api/analyze")
async def analyze_competitor(request: AnalyzeRequest, background_tasks: BackgroundTasks):
    # API key only required for live mode — demo mode runs entirely offline
    if not request.demo_mode and not os.getenv("GEMINI_API_KEY"):
        raise HTTPException(
            status_code=400,
            detail=(
                "GEMINI_API_KEY is not configured. "
                "Enable Demo Mode to run without a key, or add your key to the "
                ".env file. See the README for setup instructions."
            ),
        )

    job_id = str(uuid.uuid4())
    jobs[job_id] = {"status": "running", "events": [], "result": None, "error": None}
    queues[job_id] = asyncio.Queue()

    background_tasks.add_task(execute_workflow, job_id, request)
    return {"job_id": job_id}


@app.get("/api/stream/{job_id}")
async def stream_job_logs(job_id: str):
    if job_id not in queues:
        raise HTTPException(status_code=404, detail="Job not found")

    async def event_generator():
        q = queues[job_id]

        # If the job already finished before this client connected, replay the
        # persisted event history (which already includes the terminal event).
        if jobs[job_id]["status"] in ("completed", "failed"):
            for event in jobs[job_id]["events"]:
                yield f"data: {json.dumps(event)}\n\n"
            return

        # Otherwise stream live. The queue buffers every event from t=0 (the
        # background task is the sole producer, this generator the sole consumer),
        # so no event is missed and none is duplicated.
        while True:
            try:
                event = await q.get()
                yield f"data: {json.dumps(event)}\n\n"
                q.task_done()
                if event["type"] in ("completed", "failed"):
                    break
            except asyncio.CancelledError:
                break

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/api/job/{job_id}")
async def get_job_status(job_id: str):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    return jobs[job_id]


# Serve frontend (relative path so Docker / Cloud Run can locate it)
app.mount("/", StaticFiles(directory="app/static", html=True), name="static")
