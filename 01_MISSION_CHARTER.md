# Mission Charter — Competitive Intelligence Agent

> **This document is the fixed contract for the project. Every build sub-agent, every
> design decision, and every scope question resolves against this charter. If a proposed
> change conflicts with this charter, the charter wins unless the human owner explicitly
> amends it here. This is the primary defense against scope drift.**

---

## 1. One-sentence mission

Build a deployable, multi-agent system that reads competitors' **technical documentation**,
extracts what their products *actually do* per use case, contrasts that reality against
their **marketing claims** and against the user's **own positioning**, and delivers
tractable, account-ready competitive intelligence — replacing static battle cards.

## 2. Why this exists (the problem, fixed)

Existing competitive-intelligence tools are programmatic, not agentic. They excel at
detecting *that* a competitor's web page changed, then hand a diff to a Product Marketing
Manager (PMM) to interpret. They lack the context to understand *what the change means*.
They do not read technical documentation, do not compare claimed capabilities against
documented reality, and produce outputs (battle cards) that are stale on arrival.

## 3. The differentiator (do not dilute)

The **Technical Analysis Agent is the star of this project.** Discovery/monitoring is
commodity and underwhelming on its own. The defensible, impressive capability is reading
API docs / KBs / developer portals and surfacing the gap between marketing claims and
documented reality.

> Example of the target output: a marketing site claims "scheduled account monitoring."
> The technical documentation reveals it only supports pre-configured schedules with no
> ability to map schedules to sub-teams. **That gap is the product.**

## 4. Track

**Agents for Business** — a problem with cost/revenue on the line (PMM efficiency,
sales enablement, competitive win rates).

## 5. Dual portfolio purpose

This is simultaneously (a) a Kaggle capstone submission and (b) a portfolio artifact the
owner can demo to potential employers. It is a sanitized, demonstrable replication of real
work done at ActiveTrack, built so it can be shown **outside the company**. No proprietary
ActiveTrack data, names, or internal IP may appear anywhere in the build.

---

## 6. In scope (what we WILL build)

- A deployable web front end (simple to build, **tight UX**) on Google Cloud Run.
- User inputs: their company (name/URL), up to 3 competitors, and user-verified
  documentation sources for each competitor (KBs, API docs, developer portals).
- User pastes a few of their own positioning points to illustrate the internal-knowledge
  connection (mocked, not a live integration).
- A runtime multi-agent system (Google ADK, Gemini) anchored on technical analysis.
- Structured, tractable output: capability reality vs. claims, pricing/positioning shifts,
  major marketing moves — in a form a PMM can act on.
- At least 3 course concepts demonstrably applied (see §9).

## 7. Out of scope (explicitly — do NOT build, illustrate instead)

- Live Salesforce / CRM connection → shown as an **illustrative button** only.
- Live internal knowledge-base integration → **mocked** via pasted positioning points.
- Automated discovery of competitor doc sources → user provides/verifies sources for now;
  noted as an extension path.
- Strategy agent, account-differentiation agent, change-tracking agent → **designed in the
  architecture and writeup as the extension path; not necessarily built.**
- Any real ActiveTrack data, customer data, or proprietary internal frameworks.

## 8. Build priority (ruthless, deadline-driven)

16 days, solo. Four agents that work beautifully beat ten that half-work.

**Core four (must be built and visibly demoable):**
1. **Discovery/Monitoring Agent** — ingests user-verified doc sources, fetches content,
   feeds the analyst. (Deliberately lean — it serves the star, it is not the star.)
2. **Technical Analysis Agent** — THE STAR. Reads docs, extracts real capabilities per use
   case, contrasts vs. marketing claims and vs. user positioning.
3. **Synthesis Agent** — turns analysis into tractable, account-ready output.
4. **Fact-Checking / QC Agent** — verifies claims and reviews quality before anything is
   presented to the user.

**Designed-not-built (architecture + writeup only):** strategy, account differentiation,
change-tracking/verification-over-time.

---

## 9. Course concepts for scoring (target ≥3 of 6)

| Concept | Demonstrated where | Status |
|---|---|---|
| Multi-agent system (ADK) | Code | **LOCKED — core architecture** |
| MCP Server | Code | **TARGET — e.g. MCP server for doc fetch/compare** |
| Deployability | Video | **TARGET — Cloud Run deploy, shown in video** |
| Antigravity | Video | Stretch — agentic build process shown |
| Security features | Code or Video | Stretch — no secrets in code, input handling |
| Agent skills (Agents CLI) | Code or Video | Stretch |

Minimum bar is 3 (the three locked/target rows). Anything beyond is upside.

## 10. Scoring map (where the 100 points live)

- Pitch / Problem-Solution-Value (30): clear central idea, tight ≤5-min YouTube video,
  ≤2,500-word writeup.
- Implementation (70): architecture quality, code quality with meaningful comments,
  clever tool use, README with diagrams. **No secrets in code.**

## 11. Definition of done

- [ ] Core four agents implemented and orchestrated via ADK.
- [ ] Tight-UX front end deployed to Cloud Run, publicly accessible, no login/paywall.
- [ ] ≥3 course concepts demonstrably applied.
- [ ] Public GitHub repo with README (problem, solution, architecture, setup, diagrams).
- [ ] No API keys / secrets / proprietary ActiveTrack data anywhere.
- [ ] ≤5-min YouTube video + cover image + writeup (≤2,500 words) + public project link.
- [ ] One submission, before deadline (solo team, 1 submission allowed).

## 12. Drift guardrails (read before adding anything)

1. Does the addition serve the Technical Analysis Agent (the star)? If not, default no.
2. Is it in §7 out-of-scope? Then illustrate, do not build.
3. Does it fit in the remaining days solo without weakening the core four? If not, defer.
4. Does it earn rubric points or portfolio credibility? If neither, cut it.
