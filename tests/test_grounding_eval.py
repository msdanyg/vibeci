"""Grounding-confidence gate.

Fails the suite if any demo gap stops grounding to a real documentation line above
threshold — i.e. if a change quietly weakens VibeCI's core "every finding is grounded"
guarantee. Mirrors the standalone runner in eval/grounding_eval.py.
"""
import app.main as main
from app.grounding import GROUND_THRESHOLD, evaluate_report
from eval.grounding_eval import COMPETITORS, run_demo_report


async def _instant(*_a, **_k):
    return None


def test_every_demo_gap_grounds_above_threshold(monkeypatch):
    # Instant pacing so the gate runs fast; monkeypatch auto-reverts after the test.
    monkeypatch.setattr(main.asyncio, "sleep", _instant)

    results = [evaluate_report(run_demo_report(c)) for c in COMPETITORS]
    all_conf = []
    for r in results:
        assert r["rows"], f"{r['competitor']} produced no gaps to ground"
        for row in r["rows"]:
            all_conf.append(row["confidence"])
            assert row["on_content_line"], (
                f"{r['competitor']} gap '{row['lens']}' grounded to a non-content line (L{row['line']})")
            assert row["confidence"] >= GROUND_THRESHOLD, (
                f"{r['competitor']} gap '{row['lens']}' confidence "
                f"{row['confidence']:.2f} < threshold {GROUND_THRESHOLD}")
        assert r["passed"]

    # corpus-level health: the average should stay comfortably strong, not just clear
    # the floor (guards against a slow drift toward the threshold).
    assert sum(all_conf) / len(all_conf) >= 0.7


def test_report_carries_grounding_for_every_gap(monkeypatch):
    # The pipeline must attach the grounding block the UI reads (per gap + aggregate).
    monkeypatch.setattr(main.asyncio, "sleep", _instant)

    report = run_demo_report("Teramind")
    assert "grounding" in report and report["grounding"]["total"] == len(report["gaps"])
    assert report["grounding"]["all_grounded"] is True
    for gap in report["gaps"]:
        g = gap.get("grounding")
        assert g and 0.0 <= g["confidence"] <= 1.0 and isinstance(g["line"], int)
