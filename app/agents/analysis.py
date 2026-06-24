from google.antigravity import Agent
from app.agents.config import get_agent_config

async def run_analysis_agent(
    competitor_name: str,
    doc_summary: str,
    marketing_claims: str,
    own_positioning: str,
    research_brief: str = None,
    api_key: str = None,
) -> str:
    """Runs the Technical Analysis Agent using the Antigravity SDK.
    
    This agent takes the documentation summary, marketing claims, and internal positioning
    to extract technical reality vs claims and feature gaps.
    """
    config = get_agent_config("analysis", api_key=api_key)
    
    async with Agent(config) as agent:
        prompt = (
            f"You are analyzing the competitor: '{competitor_name}'.\n\n"
            f"### Raw Technical Specs / KB Summary:\n{doc_summary}\n\n"
            f"### Competitor Marketing Claims:\n{marketing_claims}\n\n"
            f"### Our Positioning (ActivTrak.com / Internal):\n{own_positioning}\n\n"
            f"### Research brief from the Strategy agent — FOLLOW THIS (which lenses to prioritize, who to frame for, which pillars to anchor in):\n{research_brief or '(none)'}\n\n"
            "Compare the competitor's marketing claims against their documented technical reality, "
            "prioritizing the lenses in the research brief and framing every gap for the brief's buyer. "
            "Identify the specific gaps where their technology does not match the marketing promises. "
            "Then contrast their offering against our positioning. "
            "Highlight features we have that they lack, or where their intrusive monitoring (like keystroke logging) "
            "contrasts with a privacy-first approach. Write a detailed analysis."
        )
        response = await agent.chat(prompt)
        return await response.text()
