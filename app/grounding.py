"""Server-side source grounding + a measurable grounding-confidence score.

This is the single source of truth for *how strongly each gap is grounded* to a
line in the competitor's own documentation. It is a faithful port of the
client-side grounding in `app/static/js/app.js` (same tokenizer, same IDF- and
number-weighted line match), lifted to the backend so that:

  • the UI displays the exact confidence the server computed (no JS/Python drift),
  • and `eval/grounding_eval.py` can *gate* on it in CI.

`ground_report(report)` attaches a `grounding` block to every gap and a report-level
aggregate. The differentiator of VibeCI is that every finding is grounded to a real
documentation line — this module makes that claim *measurable* rather than asserted.
"""
from __future__ import annotations

import math
import re
from typing import Any

# Token model — kept identical to app.js (STOP / tokens / weighted) so the score
# the server computes matches what the page would compute from the same text.
_STOP = set(
    "the a an of to is are and or for with by per in on at as be it that this their "
    "there into up under over its can will not no any".split()
)
_WORD = re.compile(r"[a-z0-9]+")

# A gap with confidence at or above this is considered "grounded". Calibrated from
# the demo corpus (see eval/grounding_eval.py — observed min sits well above it).
GROUND_THRESHOLD = 0.45


def tokens(text: str) -> list[str]:
    return [t for t in _WORD.findall((text or "").lower()) if len(t) > 2 and t not in _STOP]


def weighted(text: str) -> dict[str, float]:
    """Token → weight, numbers counted 3× (a specific figure is a strong anchor)."""
    m: dict[str, float] = {}
    for w in tokens(text):
        m[w] = (3 if w[0].isdigit() else 1) + m.get(w, 0)
    return m


def _doc_frame(raw_doc: str):
    """Content lines + document frequencies for IDF weighting (headers/blanks excluded)."""
    lines = (raw_doc or "").split("\n")
    content = [l for l in lines if l.strip() and not l.startswith("#")]
    df: dict[str, int] = {}
    for l in content:
        for w in set(tokens(l)):
            df[w] = df.get(w, 0) + 1
    return lines, df, len(content)


def _idf(w: str, df: dict[str, int], n: int) -> float:
    return math.log((n + 1) / (df.get(w, 0) + 1)) + 0.35  # rare token → higher weight


def _best_line(anchor: str, lines: list[str], df: dict[str, int], n: int):
    """Doc line that best matches `anchor`, plus a 0–1 confidence = matched / self.

    `self_score` is the score the anchor would earn against a line containing all of
    its own distinctive tokens, so confidence is the *fraction* of the anchor's
    weighted signal that the best line actually carries.
    """
    want = weighted(anchor)
    self_score = sum(wt * _idf(w, df, n) for w, wt in want.items())
    best = {"score": -1.0, "line": 0, "text": ""}
    for i, raw in enumerate(lines):
        if raw.startswith("#") or not raw.strip():
            continue
        score, seen = 0.0, set()
        for w in tokens(raw):
            if w not in want or w in seen:
                continue
            seen.add(w)
            score += want[w] * _idf(w, df, n)
        if score > best["score"]:
            best = {"score": score, "line": i, "text": raw}
    confidence = 0.0 if self_score <= 0 else min(1.0, best["score"] / self_score)
    return best, round(confidence, 4)


def _sections(lines: list[str]) -> list[dict[str, Any]]:
    out = []
    for i, raw in enumerate(lines):
        if raw.startswith("## "):
            out.append({"line": i, "title": raw[3:]})
    return out


def _section_label(secs: list[dict[str, Any]], line: int) -> str:
    label = ""
    for s in secs:
        if s["line"] <= line:
            m = re.match(r"^(\d+)\.\s*(.*)$", s["title"])
            label = f"{m.group(1)} · {' '.join(m.group(2).split()[:2])}" if m else s["title"]
    return label


def ground_gap(gap: dict[str, Any], raw_doc: str, preliminary_gaps: list[dict] | None) -> dict[str, Any]:
    """Ground one gap to its best documentation line and score the match 0–1.

    Mirrors app.js `groundGap`: prefer the real evidence the `compare_claims_to_docs`
    MCP tool extracted (anchor on the matching pre-screen `doc_snippet`, matched by
    overlap with this gap's TECHNICAL REALITY), then fall back to the reality text.
    """
    lines, df, n = _doc_frame(raw_doc)
    anchor = gap.get("technical_reality", "")

    if preliminary_gaps:
        claim_l = (gap.get("marketing_claim", "") + " " + gap.get("technical_reality", "")).lower()
        reality_set = set(tokens(gap.get("technical_reality", "")))
        best_p, bp = None, 0.0
        for p in preliminary_gaps:
            snippet = p.get("doc_snippet")
            if not snippet or (p.get("claim_keyword") or "none") == "none":
                continue
            s = 0.0
            for w in set(tokens(snippet)):
                if w in reality_set:
                    s += 3 if w[0].isdigit() else 1
            if p.get("claim_keyword") and p["claim_keyword"].lower() in claim_l:
                s += 1.5
            for ev in p.get("contradiction_evidence", []) or []:
                if str(ev).lower() in claim_l:
                    s += 0.5
            if s > bp:
                bp, best_p = s, p
        if best_p and bp >= 2:
            anchor = best_p["doc_snippet"]

    best, confidence = _best_line(anchor, lines, df, n)
    quote = re.sub(r"^[-*\s]+", "", best["text"]).replace("**", "").split(":")[-1].strip()
    return {
        "line": best["line"],
        "section": _section_label(_sections(lines), best["line"]),
        "quote": quote,
        "confidence": confidence,
    }


def ground_report(report: dict[str, Any], threshold: float = GROUND_THRESHOLD) -> dict[str, Any]:
    """Attach a `grounding` block to every gap + a report-level aggregate (in place)."""
    raw_doc = report.get("raw_doc", "")
    prelim = report.get("preliminary_gaps", [])
    gaps = report.get("gaps", []) or []
    confidences = []
    for gap in gaps:
        g = ground_gap(gap, raw_doc, prelim)
        gap["grounding"] = g
        confidences.append(g["confidence"])
    grounded = sum(1 for c in confidences if c >= threshold)
    report["grounding"] = {
        "score": round(sum(confidences) / len(confidences), 4) if confidences else 0.0,
        "min": round(min(confidences), 4) if confidences else 0.0,
        "grounded": grounded,
        "total": len(gaps),
        "threshold": threshold,
        "all_grounded": grounded == len(gaps) and len(gaps) > 0,
    }
    return report


def evaluate_report(report: dict[str, Any], threshold: float = GROUND_THRESHOLD) -> dict[str, Any]:
    """Run grounding and return a structured eval verdict (per-gap + aggregate)."""
    ground_report(report, threshold)
    lines = (report.get("raw_doc", "") or "").split("\n")
    rows = []
    for gap in report.get("gaps", []) or []:
        g = gap["grounding"]
        ln = g["line"]
        on_content_line = 0 <= ln < len(lines) and bool(lines[ln].strip()) and not lines[ln].startswith("#")
        rows.append({
            "lens": gap.get("lens") or gap.get("severity", ""),
            "claim": gap.get("marketing_claim", "")[:60],
            "line": ln,
            "confidence": g["confidence"],
            "on_content_line": on_content_line,
            "passed": g["confidence"] >= threshold and on_content_line,
        })
    agg = report["grounding"]
    return {
        "competitor": report.get("competitor_name", ""),
        "rows": rows,
        "avg": agg["score"],
        "min": agg["min"],
        "passed": all(r["passed"] for r in rows) and len(rows) > 0,
        "threshold": threshold,
    }
