# VibeCI — Competitive Intelligence, Grounded in the Docs

**Kaggle · AI Agents: Intensive Vibe Coding — Capstone** · Track: **Agents for Business**

- **Live demo (no login, no key):** https://vibeci-107532323288.us-central1.run.app
- **Code:** https://github.com/msdanyg/vibeci
- **Video:** https://youtu.be/uwQ-sPUDyfY

> _≤ 2,500 words (this draft ~1,700). **Track: Agents for Business.** Required attachments — a cover image (`assets/cover.png`) and a ≤5-min YouTube video — are ready. Key concepts confirmed against the competition page's Evaluation table (see §7)._

---

## 1. The problem (Agents for Business)

Competitive intelligence is one of the most expensive manual jobs in a software company. To brief a sales team on a rival, a Product Marketing Manager has to read the competitor's API docs, knowledge base, and developer portal, line them up against the competitor's marketing site, find where the *claims* break down against the *documented reality*, and hand sales a battle card. It is slow, it needs a technically literate reader, and it is stale the moment the competitor ships an update.

Existing CI tools are programmatic, not agentic: they detect *that* a competitor's web page changed and hand a diff to a human to interpret. They do not read technical documentation, and they do not reason about what a change *means* for a deal.

There is real money on the line here — PMM hours, sales-rep ramp time, and competitive win rates — which is what puts this squarely in **Agents for Business**.

## 2. What VibeCI does

VibeCI is a deployable, multi-agent system that automates that job. You give it a competitor, a documentation URL, the competitor's marketing claims, and *your own* positioning. A pipeline of agents reads the competitor's technical docs, surfaces the gaps between marketing claims and documented reality, and returns a structured, account-ready **sales battle card** — with **every finding grounded to the exact line** in the competitor's own documentation.

The output is the product: a marketing site says "real-time monitoring," the docs reveal screenshots upload asynchronously with a 2–5 minute latency, and that gap becomes a sales talking point with a citation behind it.

## 3. The differentiator: claim vs. documented reality

The deliberate centerpiece is the **Technical Analysis agent**. Discovery and monitoring are commodity; the defensible capability is *reading the docs and contrasting claimed capabilities against documented reality*. Everything in the architecture serves that agent.

Crucially, the grounding is **real and measured**, not asserted (see §5).

## 4. Architecture

A five-agent pipeline runs over an MCP tool server, built on the **`google.antigravity`** SDK and **Gemini 2.0 Flash**, served by **FastAPI** and streamed to a vanilla-JS front end over **Server-Sent Events**.

```
Strategy → Discovery → Technical Analysis ★ → Synthesis → Fact-Checking
```

- **Strategy** reads *your* business context (messaging pillars · roadmap · ICP) and emits a **Research Brief** — a directive, prioritized lenses, and the pillars to anchor the battle card in — that *directs the rest of the pipeline*.
- **Discovery** ingests the competitor's docs through the **MCP tool server** (it is the one agent that acts as a real MCP client over stdio).
- **Technical Analysis ★** — the star — performs the high-reasoning claim-vs-reality contrast.
- **Synthesis** structures the findings into a schema-validated battle card.
- **Fact-Checking** grounds every claim back to the source and drops anything unsupported.

The agents are **genuinely specialized**: each runs at a reasoning level (`ThinkingLevel`) tuned to its job — Discovery low (cheap, high-throughput ingestion), Technical Analysis and Fact-Checking high, Synthesis medium. The live run timeline surfaces each agent's model, reasoning level, and the **real MCP tool calls** it made (arguments in, structured results out).

**MCP tool server** (`FastMCP`, stdio) exposes two tools: `fetch_competitor_docs` (live HTTP GET with a mock fallback) and `compare_claims_to_docs` (a keyword-level pre-screen that extracts the doc snippets contradicting each claim — these become the grounding anchors).

**Structured output**: the final report is validated against a Pydantic `CompetitorReport` schema (battle card, claim-gaps, objection handlers, sales landmines), so the output is structured data, not a wall of text — viewable in-app as schema-validated JSON.

## 5. Grounding you can trust — measured and gated

VibeCI's core claim is that *every finding traces to a real line in the competitor's docs*. We turn that from a slogan into a metric:

- **Real grounding** (`app/grounding.py`): each gap is anchored on the evidence the MCP pre-screen tool extracted, then matched to the best documentation line by IDF- and number-weighted token overlap. No hardcoded citations — click a citation in the UI and it scrolls to and highlights the exact source line.
- **Confidence score**: each gap gets a 0–1 grounding-confidence (the fraction of the finding's distinctive, weighted tokens present in its source line), shown as a pill on every gap card. The "Grounded" stat is *earned*, not asserted.
- **An eval gate** (`eval/grounding_eval.py`): runs the real pipeline and fails (non-zero exit) if any finding falls below threshold. It is wired into the test suite **and runs in CI on every push** (GitHub Actions, green badge). Current corpus: **8/8 gaps grounded ≥ 45%, average confidence 89%**. The page shows exactly the score CI verifies.

This is the part I am proudest of — and it exists because of how the project was built (§8).

## 6. Strategy-directed, not generic doc-diffing

The reframe that makes VibeCI more than a doc-diff: it starts from *your* strategy. The Strategy agent turns your business context — pulled from mocked connectors to Confluence (messaging), Productboard (roadmap), and Salesforce (solution map / ICP) — into the research brief that steers Discovery and Analysis. Every gap is then tagged with the lens it answers, and the battle card is anchored in your pillars and framed for your buyer. A **competitive-landscape** view scores the whole field on the dimensions your strategy cares about, so you see exactly where you win.

## 7. Course concepts demonstrated

The capstone requires demonstrating **at least three** of the course's key concepts. VibeCI demonstrates **five** (using the official concept names, with where each is shown):

| Key concept | Where | In VibeCI |
|---|---|---|
| **Agent / Multi-agent system** | Code | Five specialized agents — Strategy → Discovery → Technical Analysis ★ → Synthesis → Fact-Checking — on the `google.antigravity` SDK, each with a role-tuned reasoning level, orchestrated as a streaming pipeline. |
| **MCP Server** | Code | A real `FastMCP` server over stdio (`fetch_competitor_docs`, `compare_claims_to_docs`); the Discovery agent calls it as an MCP client, with tool I/O surfaced live in the UI. |
| **Deployability** | Video | Public, keyless **Google Cloud Run** deployment (no login), shown in the video; reproducible from the `Dockerfile`. |
| **Security features** | Code | No secrets in code; bring-your-own-key live mode (per-request, masked, never stored); an SSRF guard restricting the live doc fetch to public hosts. |
| **Antigravity** | Video | Built on the `google.antigravity` SDK; the agentic, vibe-coded build process is shown in the video. |

Beyond the required concepts, the project adds engineering rigor that isn't on the rubric but strengthens it: Pydantic-validated **structured output**, real **source grounding**, and a **grounding-confidence eval** gated in CI.

## 8. How it was built — vibe-coded

This was built the way the course intends. I did not hand-write most of the code; I **directed a team of coding agents** — I described the product and the agents planned, implemented, and reviewed it. The SaaS-grade redesign was negotiated by a committee of specialized UI/UX agents. The defining moment: during a review pass, the agents caught that an early version of the source grounding was **faked** — a hardcoded citation array — and flagged it independently. So we rebuilt it for real, which became the eval-gated confidence score above. That is the point of agentic development: agents that don't just write code, but catch their own shortcuts — kept honest by a test suite and a CI eval.

## 9. Demo vs. live, and honesty

- **Demo mode** (default) is deterministic, needs no API key, and is clearly labelled "Demo data" — the canonical, always-on showcase.
- **Live mode** runs the real five-agent Gemini pipeline on a bring-your-own key (per-request, masked, never stored). The public deploy ships no key.
- The project is a sanitized, public-docs-only replication of a real competitive-intelligence workflow; no proprietary data appears anywhere. Mocked connectors are clearly labelled illustrative.

## 10. Limitations & extension path

Automated discovery of competitor doc sources, live CRM/knowledge-base integration, and a change-tracking agent are designed in the architecture as the next steps, not built — the build prioritized making the core pipeline and its grounding excellent over breadth.

---

**Try it:** https://vibeci-107532323288.us-central1.run.app · **Code:** https://github.com/msdanyg/vibeci · **Video:** https://youtu.be/uwQ-sPUDyfY
