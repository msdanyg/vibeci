# VibeCI — 3-Minute Submission Video Script

**Track:** Agents for Business · Kaggle "AI Agents: Intensive Vibe Coding"
**Runtime:** ~3:00 · **Format:** screen recording + voiceover (no face needed)
**Live demo to record against:** https://vibeci-107532323288.us-central1.run.app (Demo mode — deterministic, no key)

**Record with:** QuickTime / Loom / OBS at 1920×1080. Hide bookmarks bar, use a clean browser profile. Record each section in one take, then cut together. Keep the cursor deliberate. Run a demo once before recording so the pipeline is warm.

---

## Shot list (timecode · on-screen action · voiceover)

> Voiceover is written to be read aloud verbatim, ~150 wpm. Total ≈ 440 words ≈ 3:00.

### 1 · The problem — 0:00–0:15
**On screen:** A competitor's marketing page in one tab ("real-time, lightweight, secure"), their API docs in another. Quick toggle between them.
**VO:** "Every product marketer does this by hand: read a competitor's marketing claims, then dig through their technical docs to find where the claims fall apart. It's slow, it needs a technical reader, and it's stale the moment they ship an update."

### 2 · The solution — 0:15–0:32
**On screen:** Cut to the VibeCI config screen (the hero headline "Catch the gap between a competitor's claims and their docs").
**VO:** "This is VibeCI — a multi-agent system that automates it. But the twist is it's not generic doc-diffing. It starts from *your* strategy. In production this runs automatically on your behalf; what you're about to see is the walkthrough."

### 3 · Business context, synced — 0:32–1:02
**On screen:** Point to the "Your business context" block as the connectors sync in (Confluence · Productboard · Salesforce → "Synced & ready"). Briefly expand "Review / edit" to show pillars / roadmap / ICP. Then pick **Teramind** and show the marketing claims field. Click **Run analysis**.
**VO:** "First it pulls your business context — messaging pillars, product roadmap, and ideal customer — from tools like Confluence, Productboard, and Salesforce. That context is what makes the analysis *yours*. Then you point it at a competitor and the claims you want to test, and run."

### 4 · The agent pipeline — 1:02–1:42
**On screen:** The run timeline. Let it play. Point to each agent as it lights up; pause on the ★ Technical Analysis agent. Point to a real MCP tool-call card (`fetch_competitor_docs`, `compare_claims_to_docs`) and the source doc streaming in on the right.
**VO:** "Five specialized agents run in sequence. A Strategy agent sets the research brief. Discovery ingests the docs through an MCP tool server — these are real tool calls, arguments in, results out. The star is the Technical Analysis agent — high-reasoning claim-versus-reality contrast. Then Synthesis structures it and a Fact-Checking agent grounds every claim back to the source."

### 5 · The payoff — claim vs. reality — 1:42–2:22
**On screen:** Results screen. Scroll the Research Brief panel (lenses, "framed for", pillars). Then a gap card — read the claim vs. the technical reality. **Click the "View source ↗" citation** and let it scroll-and-highlight the exact doc line. Point to the **"100% grounded" / "56% grounded" confidence pills** and the "Grounded · avg conf" stat.
**VO:** "Here's the output: a sales battle card. Each gap pairs a marketing claim with what the docs actually say — framed for your buyer and anchored in your pillars. And every finding is grounded: click a citation and it jumps to the exact line in their own documentation. We don't just claim that — each finding carries a grounding-confidence score, shown right here."

### 6 · The whole field — 2:22–2:38
**On screen:** Back to config → **Compare the field →**. Show the landscape heatmap; run the cursor down the ActivTrak ✓ column.
**VO:** "One more view: the whole competitive field at a glance — every rival scored on the dimensions your strategy cares about, so you can see exactly where you win."

### 7 · Under the hood + the eval — 2:38–2:55
**On screen:** A terminal running `python -m eval.grounding_eval` showing the PASS table (8/8 grounded, avg 89%). Optional quick flash of the "What just happened" screen.
**VO:** "Under the hood: the `google.antigravity` SDK, an MCP tool server, Pydantic-validated output — and an eval that gates that grounding score in CI, so 'every finding is grounded' is measured, not asserted. I built this with an agentic workflow in Antigravity."

### 8 · Close — 2:55–3:00
**On screen:** The live URL + "Deployed on Google Cloud Run". End card with the repo + LinkedIn.
**VO:** "It's live on Cloud Run — go try it. Thanks for watching."

---

## Teleprompter version (VO only)

Every product marketer does this by hand: read a competitor's marketing claims, then dig through their technical docs to find where the claims fall apart. It's slow, it needs a technical reader, and it's stale the moment they ship an update.

This is VibeCI — a multi-agent system that automates it. But the twist is it's not generic doc-diffing. It starts from *your* strategy. In production this runs automatically on your behalf; what you're about to see is the walkthrough.

First it pulls your business context — messaging pillars, product roadmap, and ideal customer — from tools like Confluence, Productboard, and Salesforce. That context is what makes the analysis *yours*. Then you point it at a competitor and the claims you want to test, and run.

Five specialized agents run in sequence. A Strategy agent sets the research brief. Discovery ingests the docs through an MCP tool server — these are real tool calls, arguments in, results out. The star is the Technical Analysis agent — high-reasoning claim-versus-reality contrast. Then Synthesis structures it and a Fact-Checking agent grounds every claim back to the source.

Here's the output: a sales battle card. Each gap pairs a marketing claim with what the docs actually say — framed for your buyer and anchored in your pillars. And every finding is grounded: click a citation and it jumps to the exact line in their own documentation. We don't just claim that — each finding carries a grounding-confidence score, shown right here.

One more view: the whole competitive field at a glance — every rival scored on the dimensions your strategy cares about, so you can see exactly where you win.

Under the hood: the `google.antigravity` SDK, an MCP tool server, Pydantic-validated output — and an eval that gates that grounding score in CI, so "every finding is grounded" is measured, not asserted. I built this with an agentic workflow in Antigravity.

It's live on Cloud Run — go try it. Thanks for watching.

---

## Recording checklist

- [ ] Warm the demo once before recording (avoids Cloud Run cold-start lag) — or record locally with `uvicorn app.main:app --port 8080`.
- [ ] Section 4 (pipeline) is the slowest beat — the demo run takes ~13s. Either let it play under the VO, or record it and speed the dead air to ~1.5×.
- [ ] Section 5: practice the citation click so the highlight lands cleanly on camera.
- [ ] Section 7: pre-run the eval so the terminal output is already on screen, then cut to it.
- [ ] End card: repo `github.com/msdanyg/vibeci` · LinkedIn `linkedin.com/in/glickmandaniel` · daniel@cmoconfessions.com
- [ ] Export 1080p, upload unlisted to YouTube, paste the link into the Kaggle writeup.

## Optional B-roll lower-thirds (on-screen text overlays)
- "5 agents · MCP tools · Gemini 2.0 Flash"
- "Every finding grounded to a source line"
- "Grounding-confidence — gated by an eval"
- "Deployed on Google Cloud Run"
