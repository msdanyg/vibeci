"""Unit tests for the MCP document tools (app/mcp_server.py).

These are the deterministic, pure-Python core of the pipeline — fetching docs
(live with a mock fallback) and the keyword pre-screen that produces the
grounding evidence. Run from the repo root: `pytest`.
"""
import json

from app.mcp_server import (
    fetch_competitor_docs,
    compare_claims_to_docs,
    _resolve_competitor_key,
)


# --------------------------------------------------------------------------- #
# _resolve_competitor_key
# --------------------------------------------------------------------------- #
def test_resolve_competitor_key_matches_known():
    assert _resolve_competitor_key("Teramind") == "teramind"
    assert _resolve_competitor_key("Hubstaff Inc.") == "hubstaff"
    assert _resolve_competitor_key("Time Doctor") == "timedoctor"
    assert _resolve_competitor_key("timedoctor") == "timedoctor"


def test_resolve_competitor_key_defaults_safely():
    assert _resolve_competitor_key("Some Unknown Vendor") == "teramind"


# --------------------------------------------------------------------------- #
# fetch_competitor_docs
# --------------------------------------------------------------------------- #
def test_fetch_uses_mock_for_known_competitor():
    doc = fetch_competitor_docs("Teramind", "")
    assert "Teramind" in doc and "350 kbps" in doc
    assert "Hubstaff" in fetch_competitor_docs("Hubstaff", "")
    assert "Time Doctor" in fetch_competitor_docs("Time Doctor", "")


def test_fetch_non_http_url_falls_back_to_mock():
    # a mock:// scheme is not http(s), so it must use preloaded specs
    doc = fetch_competitor_docs("Teramind", "mock://teramind-kb.org/specs")
    assert "Teramind API" in doc


def test_fetch_live_http_returns_truncated_body(monkeypatch):
    class FakeResp:
        status_code = 200
        text = "LIVE DOCUMENTATION CONTENT " * 500  # > 8000 chars

    class FakeClient:
        def __init__(self, *a, **k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def get(self, url, **k):
            return FakeResp()

    monkeypatch.setattr("app.mcp_server.httpx.Client", FakeClient)
    monkeypatch.setattr("app.mcp_server._is_public_http_url", lambda url: True)  # isolate from the SSRF guard
    doc = fetch_competitor_docs("Teramind", "https://docs.example.com")
    assert doc.startswith("LIVE DOCUMENTATION CONTENT")
    assert len(doc) <= 8000  # truncation enforced


def test_fetch_live_http_failure_falls_back_to_mock(monkeypatch):
    class BoomClient:
        def __init__(self, *a, **k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def get(self, url, **k):
            raise RuntimeError("network down")

    monkeypatch.setattr("app.mcp_server.httpx.Client", BoomClient)
    monkeypatch.setattr("app.mcp_server._is_public_http_url", lambda url: True)  # isolate from the SSRF guard
    doc = fetch_competitor_docs("Teramind", "https://docs.example.com")
    assert "Teramind API" in doc  # fell back to the preloaded spec


def test_fetch_blocks_ssrf_to_private_hosts(monkeypatch):
    """A private/loopback/metadata URL must never be fetched — it falls back to mock."""
    attempts = {"n": 0}

    class SpyClient:
        def __init__(self, *a, **k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def get(self, url, **k):
            attempts["n"] += 1

            class _R:
                status_code = 200
                text = "SECRET INTERNAL DATA"
            return _R()

    monkeypatch.setattr("app.mcp_server.httpx.Client", SpyClient)

    # literal hosts → no real DNS needed
    for bad in (
        "http://169.254.169.254/latest/meta-data/",  # cloud metadata
        "http://127.0.0.1:8080/admin",               # loopback
        "http://localhost/internal",                 # loopback by name
        "http://10.0.0.5/secrets",                   # private range
        "ftp://example.com/docs",                    # non-http scheme
    ):
        doc = fetch_competitor_docs("Teramind", bad)
        assert "Teramind API" in doc  # fell back to the mock spec

    assert attempts["n"] == 0  # the live client was never invoked


# --------------------------------------------------------------------------- #
# compare_claims_to_docs (the grounding pre-screen)
# --------------------------------------------------------------------------- #
def test_compare_flags_real_time_contradiction():
    claims = "Real-time monitoring with zero-latency alerts."
    docs = (
        "Screenshots are uploaded asynchronously; there is a latency of "
        "2 to 5 minutes before a live session appears."
    )
    out = json.loads(compare_claims_to_docs(claims, docs))
    gaps = out["preliminary_gaps"]
    keywords = {g.get("claim_keyword") for g in gaps}
    assert "real-time" in keywords

    rt = next(g for g in gaps if g.get("claim_keyword") == "real-time")
    assert rt["contradiction_evidence"]          # found contradicting terms
    assert rt["doc_snippet"]                      # carries a real doc excerpt
    assert "POTENTIAL GAP" in rt["flag"]


def test_compare_returns_none_entry_when_no_signal():
    out = json.loads(compare_claims_to_docs("Our product is friendly and helpful.",
                                            "Neutral documentation with no triggers."))
    gaps = out["preliminary_gaps"]
    assert len(gaps) == 1
    assert gaps[0]["claim_keyword"] == "none"


def test_compare_output_is_valid_json_with_expected_shape():
    out = json.loads(compare_claims_to_docs("lightweight agent", "requires 350 kbps bandwidth"))
    assert "preliminary_gaps" in out
    assert isinstance(out["preliminary_gaps"], list)
