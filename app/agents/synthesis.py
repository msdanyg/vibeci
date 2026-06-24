from pydantic import BaseModel
from google.antigravity import Agent
from app.agents.config import get_agent_config

# Pydantic schemas for structured Competitive Intelligence output
class ClaimGap(BaseModel):
    marketing_claim: str
    technical_reality: str
    severity: str  # e.g., 'High Gaps', 'Moderate Gaps', 'Minor Gaps'
    sales_impact: str

class ObjectionHandler(BaseModel):
    competitor_objection: str
    our_response: str

class BattleCard(BaseModel):
    elevator_pitch: str
    strengths: list[str]
    weaknesses: list[str]
    objection_handling: list[ObjectionHandler]

class CompetitorReport(BaseModel):
    competitor_name: str
    key_takeaways: list[str]
    gaps: list[ClaimGap]
    battle_card: BattleCard
    sales_landmines: list[str]

async def run_synthesis_agent(competitor_name: str, analysis_details: str, api_key: str = None) -> CompetitorReport:
    """Runs the Synthesis Agent using the Antigravity SDK to generate structured competitive reports.
    
    This agent takes the technical analysis details and generates a Pydantic-validated JSON output
    that matches the CompetitorReport schema.
    """
    # Create config with response_schema
    config = get_agent_config("synthesis", response_schema=CompetitorReport, api_key=api_key)
    
    async with Agent(config) as agent:
        prompt = (
            f"You are synthesizing the competitive intelligence for competitor '{competitor_name}'.\n\n"
            f"### Technical Analysis details:\n{analysis_details}\n\n"
            "Format your response to match the requested JSON schema. Populate all fields: key takeaways, "
            "the list of claim-vs-reality gaps (marketing claim, technical reality, severity, sales impact), "
            "the sales battle card (elevator pitch, strengths, weaknesses, objection handling), and specific "
            "sales landmines. Make sure the content is highly detailed and directly references facts from the analysis."
        )
        response = await agent.chat(prompt)
        structured_data = await response.structured_output()
        
        # If parsing fails or structured output isn't parsed automatically, return a model instance
        if isinstance(structured_data, dict):
            return CompetitorReport(**structured_data)
        return structured_data
