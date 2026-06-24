#!/usr/bin/env python3
"""Grounding-confidence eval — VibeCI's core claim, measured and gated.

VibeCI's differentiator is that every finding is grounded to a line in the
competitor's *own* documentation. This harness turns that from a marketing claim
into a measured, gated metric: it runs the real demo pipeline for each competitor,
scores how strongly each gap is backed by its source line (app/grounding.py — the
same code the UI shows), and fails (non-zero exit) if any gap falls below threshold.

Run from the repo root:

    python -m eval.grounding_eval        # prints the report, exits 1 on any failure

It is also wired as a pytest gate (tests/test_grounding_eval.py) so the suite fails
if a future change weakens grounding.
"""
from __future__ import annotations

import asyncio
import sys

import app.main as main
from app.grounding import GROUND_THRESHOLD, evaluate_report

COMPETITORS = ["Teramind", "Hubstaff", "Time Doctor"]


async def _instant(*_a, **_k):
    return None


def run_demo_report(competitor: str) -> dict:
    """Drive the real demo pipeline once and return the completed report."""
    job_id = f"eval-{competitor.lower().replace(' ', '-')}"
    main.jobs[job_id] = {"status": "running", "events": [], "result": None, "error": None}
    main.queues[job_id] = asyncio.Queue()
    req = main.AnalyzeRequest(
        competitor_name=competitor,
        doc_url="mock://eval",
        marketing_claims="Real-time, accurate, lightweight, non-intrusive monitoring.",
        own_positioning="Privacy-first workforce analytics.",
        demo_mode=True,
    )
    asyncio.run(main.execute_workflow(job_id, req))
    report = main.jobs[job_id]["result"]
    main.jobs.pop(job_id, None)
    main.queues.pop(job_id, None)
    if not report:
        raise RuntimeError(f"pipeline produced no report for {competitor}")
    return report


def evaluate_all(threshold: float = GROUND_THRESHOLD) -> list[dict]:
    # Instant pacing so the eval runs in well under a second.
    main.asyncio.sleep = _instant  # type: ignore[assignment]
    return [evaluate_report(run_demo_report(c), threshold) for c in COMPETITORS]


def _bar(conf: float, width: int = 20) -> str:
    filled = round(conf * width)
    return "█" * filled + "·" * (width - filled)


def main_cli() -> int:
    results = evaluate_all()
    all_conf: list[float] = []
    print("\n  VibeCI · GROUNDING-CONFIDENCE EVAL")
    print(f"  Every gap must ground to a real doc line with confidence ≥ {GROUND_THRESHOLD:.0%}\n")
    print("  " + "─" * 78)
    for r in results:
        verdict = "PASS" if r["passed"] else "FAIL"
        print(f"  {r['competitor']:<14} avg {r['avg']:.0%}   min {r['min']:.0%}   [{verdict}]")
        for row in r["rows"]:
            all_conf.append(row["confidence"])
            mark = "✓" if row["passed"] else "✗"
            line_ok = "" if row["on_content_line"] else "  ⚠ not a content line"
            print(f"      {mark} {row['confidence']:.0%} {_bar(row['confidence'])} "
                  f"L{row['line']:<3} {row['lens'][:24]:<24}{line_ok}")
        print("  " + "─" * 78)

    n = len(all_conf)
    grounded = sum(1 for c in all_conf if c >= GROUND_THRESHOLD)
    overall_avg = sum(all_conf) / n if n else 0.0
    passed = all(r["passed"] for r in results)
    print(f"\n  CORPUS: {grounded}/{n} gaps grounded ≥ {GROUND_THRESHOLD:.0%}  ·  "
          f"avg confidence {overall_avg:.0%}  ·  min {min(all_conf):.0%}")
    print(f"  RESULT: {'✓ PASS — grounding holds across the corpus' if passed else '✗ FAIL — grounding regressed'}\n")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main_cli())
