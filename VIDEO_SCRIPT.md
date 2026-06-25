# VibeCI — Submission Video Script (~3:00)

**Track:** Agents for Business · Kaggle "AI Agents: Intensive Vibe Coding"
**Runtime:** ~3:00 · **Format:** screen recording + voiceover (no face needed)
**Live demo to record against:** https://vibeci-107532323288.us-central1.run.app (Demo mode — deterministic, no key)

**Record with:** QuickTime / Loom / OBS at 1920×1080. Hide the bookmarks bar, use a clean browser profile. Record each section in one take, then cut together. Keep the cursor deliberate. Warm a demo run once before recording so the pipeline is fast.

> The first half is the product demo; the back third is **under the hood** + **how it was built** — that's where this competition is won, so it's expanded. Total VO ≈ 640 words. If you read fast and it runs short, slow down on sections 4, 7, and 8 and let the on-screen action breathe.
>
> `[brackets]` = pick/confirm before recording (e.g. name your build tool). Don't read them aloud.

---

## Shot list (timecode · on-screen action · voiceover)

### 1 · The problem — 0:00–0:15
**On screen:** A competitor's marketing page in one tab ("real-time, lightweight, secure"), their API docs in another. Toggle between them.
**VO:** "Every product marketer does this by hand: read a competitor's marketing claims, then dig through their technical docs to find where the claims fall apart. It's slow, it needs a technical reader, and it's stale the moment they ship an update."

### 2 · The solution — 0:15–0:33
**On screen:** Cut to the VibeCI config screen (hero: "Catch the gap between a competitor's claims and their docs").
**VO:** "This is VibeCI — a multi-agent system that automates it. The twist: it's not generic doc-diffing, it starts from *your* strategy. In production this runs automatically on your behalf; what you're about to see is the walkthrough."

### 3 · Business context, synced — 0:33–1:00
**On screen:** Point to the "Your business context" block as the connectors sync (Confluence · Productboard · Salesforce → "Synced & ready"). Briefly expand "Review / edit" to flash pillars / roadmap / ICP. Pick **Teramind**, show the claims field, click **Run analysis**.
**VO:** "First it pulls your business context — messaging pillars, product roadmap, ideal customer — from tools like Confluence, Productboard, and Salesforce. That's what makes the analysis *yours*. Then you point it at a competitor and the claims you want to test, and run."

### 4 · The agent pipeline — 1:00–1:38
**On screen:** The run timeline. Let it play. Point to each agent as it lights up; **pause on the labels showing each agent's reasoning level**; linger on the ★ Technical Analysis agent. Point to a real MCP tool-call card (`fetch_competitor_docs`, `compare_claims_to_docs`) and the source doc streaming in on the right.
**VO:** "Five specialized agents run in sequence — and they're genuinely specialized. Each one runs at a different reasoning level tuned to its job: Discovery ingests the docs cheaply and fast; the star Technical Analysis agent runs high-reasoning to contrast every claim against documented reality; Fact-Checking runs high too. Discovery reaches the docs through an MCP tool server — these are real tool calls, arguments in, structured results out — and you can watch the source document stream in live."

### 5 · The payoff — claim vs. reality — 1:38–2:12
**On screen:** Results screen. Scroll the Research Brief panel (lenses, "framed for", pillars). Open a gap card. **Click "View source ↗"** and let it scroll-and-highlight the exact doc line. Point to the **confidence pills** ("100% grounded" / "56% grounded") and the earned "Grounded · avg conf" stat.
**VO:** "Here's the output: a sales battle card. Each gap pairs a marketing claim with what the docs actually say — framed for your buyer, anchored in your pillars. And every finding is grounded: click a citation, and it jumps to the exact line in the competitor's own docs. We don't just claim that — each finding carries a grounding-confidence score, right on the card."

### 6 · The whole field — 2:12–2:24
**On screen:** Back to config → **Compare the field →**. Show the landscape heatmap; run the cursor down the ActivTrak ✓ column.
**VO:** "And a field view: every rival scored on the dimensions your strategy cares about — so you see exactly where you win."

### 7 · Under the hood — 2:24–2:48
**On screen:** Open the **"Structured output"** expandable to show the schema-validated JSON. Then a terminal running `python -m eval.grounding_eval` showing the PASS table (8/8, avg 89%). Optionally flash the architecture: the SSE timeline / the MCP tool cards.
**VO:** "Under the hood: the `google.antigravity` SDK on Gemini 2.0 Flash, orchestrated as a streaming pipeline — every step emits typed events that drive that live timeline. The agents talk to an MCP tool server over stdio. The final report is validated against a Pydantic schema, so the output is structured, not a wall of text. And the grounding isn't a vibe — it's a real algorithm, anchored on the evidence the tools extracted, and gated by an eval in CI. So 'every finding is grounded' is *measured*, and the page shows exactly the score the eval verifies."

### 8 · How it was built — 2:48–3:08
**On screen:** B-roll of the codebase / your agent IDE — `app/agents/`, the eval, the commit history — or just stay on the running app.
**VO:** "And it was built the way the competition intends — vibe-coded. I didn't hand-write most of this; I directed a team of coding agents: described the product, and they planned, implemented, and reviewed it. The redesign you're looking at was negotiated by a committee of UI and UX agents. The best moment: during review, the agents caught that an early version of the source grounding was *faked* — hardcoded citations — and flagged it. So we rebuilt it for real. That's the whole point: agents that don't just write code, but catch their own shortcuts — kept honest by tests and that grounding eval. `[Built in <your tool — Antigravity / Claude Code>.]`"

### 9 · Close — 3:08–3:15
**On screen:** Live URL + "Deployed on Google Cloud Run". End card: repo + LinkedIn + email.
**VO:** "It's live on Cloud Run — go try it. Thanks for watching."

---

## Teleprompter version (VO only)

Every product marketer does this by hand: read a competitor's marketing claims, then dig through their technical docs to find where the claims fall apart. It's slow, it needs a technical reader, and it's stale the moment they ship an update.

This is VibeCI — a multi-agent system that automates it. The twist: it's not generic doc-diffing, it starts from *your* strategy. In production this runs automatically on your behalf; what you're about to see is the walkthrough.

First it pulls your business context — messaging pillars, product roadmap, ideal customer — from tools like Confluence, Productboard, and Salesforce. That's what makes the analysis *yours*. Then you point it at a competitor and the claims you want to test, and run.

Five specialized agents run in sequence — and they're genuinely specialized. Each one runs at a different reasoning level tuned to its job: Discovery ingests the docs cheaply and fast; the star Technical Analysis agent runs high-reasoning to contrast every claim against documented reality; Fact-Checking runs high too. Discovery reaches the docs through an MCP tool server — these are real tool calls, arguments in, structured results out — and you can watch the source document stream in live.

Here's the output: a sales battle card. Each gap pairs a marketing claim with what the docs actually say — framed for your buyer, anchored in your pillars. And every finding is grounded: click a citation, and it jumps to the exact line in the competitor's own docs. We don't just claim that — each finding carries a grounding-confidence score, right on the card.

And a field view: every rival scored on the dimensions your strategy cares about — so you see exactly where you win.

Under the hood: the `google.antigravity` SDK on Gemini 2.0 Flash, orchestrated as a streaming pipeline — every step emits typed events that drive that live timeline. The agents talk to an MCP tool server over stdio. The final report is validated against a Pydantic schema, so the output is structured, not a wall of text. And the grounding isn't a vibe — it's a real algorithm, anchored on the evidence the tools extracted, and gated by an eval in CI. So "every finding is grounded" is measured, and the page shows exactly the score the eval verifies.

And it was built the way the competition intends — vibe-coded. I didn't hand-write most of this; I directed a team of coding agents: described the product, and they planned, implemented, and reviewed it. The redesign you're looking at was negotiated by a committee of UI and UX agents. The best moment: during review, the agents caught that an early version of the source grounding was *faked* — hardcoded citations — and flagged it. So we rebuilt it for real. That's the whole point: agents that don't just write code, but catch their own shortcuts — kept honest by tests and that grounding eval.

It's live on Cloud Run — go try it. Thanks for watching.

---

## Recording checklist

- [ ] Warm the demo once before recording (avoids Cloud Run cold-start lag) — or record locally with `uvicorn app.main:app --port 8080`.
- [ ] Section 4 (pipeline) is the slowest beat — the demo run takes ~13s. Let it play under the VO, or record it and speed the dead air to ~1.5×.
- [ ] Section 5: practice the citation click so the highlight lands cleanly on camera.
- [ ] Section 7: pre-run `python -m eval.grounding_eval` so the PASS table is already on screen, then cut to it. Have the "Structured output" panel open before you start narrating.
- [ ] Section 8: decide your B-roll — the cleanest option is the codebase tree (`app/agents/`, `app/grounding.py`, `eval/`) or your agent IDE's history. Confirm the `[your tool]` line.
- [ ] End card: repo `github.com/msdanyg/vibeci` · LinkedIn `linkedin.com/in/glickmandaniel` · daniel@cmoconfessions.com
- [ ] Export 1080p, upload unlisted to YouTube, paste the link into the Kaggle writeup.

## Optional on-screen lower-thirds (text overlays)
- "5 agents · per-agent reasoning levels"
- "Real MCP tool calls · stdio"
- "Pydantic-validated structured output"
- "Grounding-confidence — gated by an eval in CI"
- "Vibe-coded: agents planned, built & reviewed it"
- "Deployed on Google Cloud Run"
