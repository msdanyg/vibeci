"""
Strategy / Research-Planning Agent — the first stage of the pipeline.

It reads the user's OWN internal business context (messaging pillars, product
roadmap, solution map / ICP) and turns it into a structured Research Brief that
DIRECTS the rest of the pipeline: which competitor capabilities to scrutinise
(prioritized "lenses"), who to frame the findings for (the ICP), and which
messaging pillars to anchor the battle card in.

This is the "the research agent knows what to look for" layer — competitive
intelligence directed by your strategy, not generic doc-diffing.
"""

from pydantic import BaseModel
from google.antigravity import Agent
from app.agents.config import get_agent_config


class ResearchLens(BaseModel):
    name: str          # e.g. "Real-time latency"
    why: str           # why this lens matters to *this* company's strategy/buyer


class ResearchBrief(BaseModel):
    directive: str             # one-sentence "what to hunt for"
    lenses: list[ResearchLens] # prioritized analysis lenses
    icp: str                   # who the findings are framed for
    pillars: list[str]         # our messaging pillars to anchor the battle card in


async def run_strategy_agent(
    competitor_name: str,
    messaging_pillars: str,
    roadmap: str,
    icp: str,
    api_key: str = None,
) -> ResearchBrief:
    """Turn internal business context into a Research Brief that steers the pipeline."""
    config = get_agent_config("strategy", response_schema=ResearchBrief, api_key=api_key)

    async with Agent(config) as agent:
        prompt = (
            f"You are planning competitive research against '{competitor_name}'.\n\n"
            f"### Our messaging pillars / positioning:\n{messaging_pillars or '(none provided)'}\n\n"
            f"### Our product roadmap:\n{roadmap or '(none provided)'}\n\n"
            f"### Our solution map / ICP (ideal customer profile):\n{icp or '(none provided)'}\n\n"
            "Produce a focused research brief matching the requested schema:\n"
            "- directive: one sentence on what this analysis should hunt for, anchored in our strategy.\n"
            "- lenses: 3–4 prioritized competitor capabilities to scrutinise, each with a short 'why' "
            "tied to our pillars or buyer. Order them by importance to us.\n"
            "- icp: the buyer/segment the findings should be written for.\n"
            "- pillars: the messaging pillars the final battle card should be anchored in.\n"
            "Do NOT analyze the competitor's docs yet — only set the agenda."
        )
        response = await agent.chat(prompt)
        brief = await response.structured_output()
        if isinstance(brief, dict):
            return ResearchBrief(**brief)
        return brief
