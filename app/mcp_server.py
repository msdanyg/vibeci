"""
MCP Server — Competitive Intelligence Document Tools

Exposes two tools via the Model Context Protocol (MCP):
  1. fetch_competitor_docs  — fetches raw technical documentation from a URL or
                              falls back to preloaded developer-spec mock data.
  2. compare_claims_to_docs — performs a keyword-level diff between a list of
                              marketing claims and a documentation body so the
                              Technical Analysis Agent has a structured starting
                              point before its LLM reasoning pass.

This server is started as a subprocess by the FastAPI backend and communicates
over stdio using the MCP JSON-RPC wire format via the `mcp` Python library.
"""

import json
import socket
import ipaddress
from urllib.parse import urlparse

import httpx
from mcp.server.fastmcp import FastMCP

# ---------------------------------------------------------------------------
# MCP server instance
# ---------------------------------------------------------------------------
mcp = FastMCP(
    name="ci-doc-tools",
    instructions=(
        "Competitive Intelligence document fetch and claims comparison tools "
        "for the VibeCI multi-agent system."
    ),
)

# ---------------------------------------------------------------------------
# Preloaded high-fidelity developer documentation (same source as discovery.py)
# Used as a safe fallback when live scraping is unavailable or rate-limited.
# ---------------------------------------------------------------------------
MOCK_DOCUMENTS: dict[str, str] = {
    "teramind": """
# Teramind API & KB Developer Documentation (v4.2)

## 1. Screen Recording and Session Player
- **Data Capture Mechanism**: Screens are captured at configured frame rates
  (default: 15 fps) and saved locally as temporary compressed blocks.
- **Upload Sync Interval**: Temporary files are packed into 5 MB chunks and
  uploaded asynchronously to the cloud storage bucket. Under default network
  conditions, there is a **latency of 2 to 5 minutes** before a live session
  shows up in the admin dashboard player.
- **OCR Engine**: Text on screen is analyzed by a background cron job running
  every 15 minutes. It is NOT real-time. Text search will only yield results
  **15 minutes after the activity occurs**.

## 2. Keystroke Logging Agent
- **Buffer Limits**: The agent buffers keyboard events locally in a 1 KB FIFO
  buffer.
- **Network Dispatch**: The buffer is flushed and sent to the server every
  **5 minutes** or immediately if the 1 KB limit is exceeded.
- **Exclusions**: Keystroke monitoring can be bypassed by application executable
  names listed in `keystroke_exclusions.json`.

## 3. Network & Bandwidth Requirements
- The desktop agent requires a persistent outbound WebSocket connection.
- Average bandwidth consumption per monitored user is **350 kbps** when screen
  recording is active, which can saturate local office connections for teams
  larger than 50 employees unless rate-limited to 5 fps.
""",
    "hubstaff": """
# Hubstaff Developer API & Time Tracking Integration Docs

## 1. Activity Scoring Algorithm
- **Tracking Epochs**: Activity is recorded in **10-minute windows (epochs)**.
- **Input Sampling**: The Hubstaff desktop client counts keyboard keystrokes and
  mouse movements (clicks and coordinate changes).
- **Productivity Calculation**:
  `Activity % = (Seconds with at least 1 input event / 600 seconds) * 100`
  *Note*: A developer writing complex code might type for 1 minute (100%) and
  think for 9 minutes (0%), resulting in a reported **10% activity score**.

## 2. Inactivity (Idle) Detection
- **Trigger Window**: The client detects inactivity after **5 consecutive
  minutes** of zero keyboard or mouse inputs.
- **User Prompt**: A modal popup asks: *"Are you still working on [Task]?"*
- **Action Required**: The employee must click "Yes" within 60 seconds or the
  idle time is automatically subtracted from their timesheet.

## 3. Screenshots (Proof of Work)
- **Interval**: Randomly taken 1–3 times per 10-minute interval.
- **Blur Ring**: Blurring is applied client-side if configured, but metadata
  (active window title, application path) is uploaded in plain text and cannot
  be blurred.
""",
    "timedoctor": """
# Time Doctor API Integration & Tracking Specifications

## 1. Window & Application Sampling
- **Active Title Collection**: Active window titles and application paths are sampled once every **15 seconds**. Short-duration transitions, rapid tab switching, or brief notifications will be missed by this sampling window.
- **Local Cache**: Collected title events are stored in a local SQLite file and uploaded in 1-minute batches.

## 2. Inactivity & Distraction Alerts
- **Idle Threshold**: A user is marked idle after **3 consecutive minutes** of zero keyboard/mouse inputs.
- **Alert Popup**: If idle while the timer runs, a popup asks: *"Are you still working?"*
- **Auto-Pause**: If not dismissed in 60 seconds, time tracking pauses. Savannah users can bypass this check using background auto-clicker scripts.

## 3. Screenshot Capture Specs
- **Sync Interval**: Screenshots are captured at random intervals (default: 3 mins, 9 mins, or 15 mins).
- **Upload Delay**: Screenshots are buffered locally, compressed, and uploaded asynchronously. On standard connections, there is an **upload delay of up to 10 minutes** before they appear in the web dashboard.
""",
}


def _is_public_http_url(url: str) -> bool:
    """Best-effort SSRF guard for the live-fetch path.

    Competitor docs live on the public internet, so we only fetch http(s) URLs
    whose host resolves entirely to public IP addresses — rejecting loopback,
    private, link-local (incl. the 169.254.169.254 cloud-metadata endpoint),
    reserved, and multicast targets. Anything that fails this check falls back
    to the preloaded mock spec rather than hitting the network.
    """
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https") or not parsed.hostname:
            return False
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        infos = socket.getaddrinfo(parsed.hostname, port, proto=socket.IPPROTO_TCP)
        if not infos:
            return False
        for info in infos:
            ip = ipaddress.ip_address(info[4][0])
            if (ip.is_private or ip.is_loopback or ip.is_link_local
                    or ip.is_reserved or ip.is_multicast or ip.is_unspecified):
                return False
        return True
    except Exception:
        # Unresolvable host, malformed URL, etc. — do not fetch.
        return False


def _resolve_competitor_key(name_or_url: str) -> str:
    """Map a free-text competitor name or URL to a known mock-data key."""
    s = name_or_url.lower()
    if "teramind" in s:
        return "teramind"
    if "hubstaff" in s:
        return "hubstaff"
    if "time doctor" in s or "timedoctor" in s:
        return "timedoctor"
    return "teramind"  # safe default


# ---------------------------------------------------------------------------
# Tool 1: fetch_competitor_docs
# ---------------------------------------------------------------------------
@mcp.tool()
def fetch_competitor_docs(competitor_name: str, doc_url: str = "") -> str:
    """Fetch technical documentation for a competitor.

    Attempts a live HTTP GET on *doc_url* first (8-second timeout). If the
    request fails, is not provided, or the URL is a mock:// placeholder, the
    tool falls back to the preloaded developer specification for that competitor.

    Args:
        competitor_name: Display name of the competitor (e.g. "Teramind").
        doc_url: Optional URL to the competitor's API docs or KB portal.

    Returns:
        Raw technical documentation as a markdown string (up to 8 000 chars).
    """
    # Attempt live fetch only for http(s) URLs that resolve to public hosts
    if doc_url and _is_public_http_url(doc_url):
        try:
            with httpx.Client(timeout=8.0) as client:
                resp = client.get(
                    doc_url,
                    headers={"User-Agent": "VibeCI-Bot/1.0 (competitive-intelligence-agent)"},
                    follow_redirects=True,
                )
                if resp.status_code == 200:
                    return resp.text[:8000]
        except Exception:
            # Network failure — fall through to mock data
            pass

    # Fallback: preloaded developer spec
    key = _resolve_competitor_key(competitor_name)
    return MOCK_DOCUMENTS.get(
        key,
        f"# Documentation for {competitor_name}\nNo preloaded documentation available.",
    )


# ---------------------------------------------------------------------------
# Tool 2: compare_claims_to_docs
# ---------------------------------------------------------------------------
@mcp.tool()
def compare_claims_to_docs(marketing_claims: str, documentation: str) -> str:
    """Perform a keyword-level pre-screen of marketing claims against documentation.

    Scans each marketing claim for high-signal keywords (e.g. "real-time",
    "instant", "zero-latency") and checks whether the documentation contains
    contradictory latency or constraint language. Returns a structured JSON
    report that the Technical Analysis Agent uses as a starting scaffold.

    Args:
        marketing_claims: Raw marketing claim text from the competitor's website.
        documentation:    The technical documentation body (from fetch_competitor_docs).

    Returns:
        A JSON string with a list of preliminary {claim, flag, context} objects.
    """
    # Keyword pairs: (marketing_signal, doc_contradiction_hints)
    SIGNAL_MAP = [
        ("real-time",      ["minutes", "latency", "delay", "async", "cron", "epoch"]),
        ("instant",        ["minutes", "buffer", "5 minutes", "15 minutes", "latency"]),
        ("zero-latency",   ["latency", "minutes", "delay", "async", "buffer"]),
        ("lightweight",    ["kbps", "bandwidth", "350", "websocket", "persistent"]),
        ("non-intrusive",  ["popup", "modal", "prompt", "interrupt", "keystroke"]),
        ("seamless",       ["popup", "modal", "prompt", "interrupt", "subtracted"]),
        ("accurate",       ["epoch", "10-minute", "sampling", "0%", "activity %"]),
        ("automated",      ["manual", "configuration", "exclusion", "config file"]),
        ("secure",         ["bypass", "exclusion", "renamed", "exclusions.json"]),
    ]

    doc_lower = documentation.lower()
    claims_lower = marketing_claims.lower()
    results = []

    for signal, contradictions in SIGNAL_MAP:
        if signal not in claims_lower:
            continue  # this signal isn't in the marketing claims — skip

        # Find which contradiction keywords appear in the docs
        hits = [c for c in contradictions if c in doc_lower]
        if hits:
            # Extract a short snippet of context around the first hit
            idx = doc_lower.find(hits[0])
            snippet = documentation[max(0, idx - 40) : idx + 120].replace("\n", " ").strip()
            results.append({
                "claim_keyword": signal,
                "contradiction_evidence": hits,
                "doc_snippet": snippet,
                "flag": "POTENTIAL GAP — verify with Technical Analysis Agent",
            })

    if not results:
        results.append({
            "claim_keyword": "none",
            "flag": "No obvious keyword contradictions found — deeper LLM analysis required.",
        })

    return json.dumps({"preliminary_gaps": results}, indent=2)


# ---------------------------------------------------------------------------
# Entrypoint — run the MCP server over stdio (standard MCP transport)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    mcp.run(transport="stdio")
