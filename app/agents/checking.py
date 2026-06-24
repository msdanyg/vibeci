from google.antigravity import Agent
from app.agents.config import get_agent_config
from app.agents.synthesis import CompetitorReport
import json

async def run_checking_agent(
    competitor_name: str,
    doc_summary: str,
    synthesis_report: CompetitorReport,
    api_key: str = None,
) -> CompetitorReport:
    """Runs the Fact-Checking / QC Agent using the Antigravity SDK.
    
    This agent compares the synthesized report contents against the raw technical specs
    to ensure absolute accuracy and safety. It outputs a validated/corrected CompetitorReport.
    """
    config = get_agent_config("checking", response_schema=CompetitorReport, api_key=api_key)
    
    # Serialize the report to JSON for the agent to inspect
    report_json = json.dumps(synthesis_report.model_dump(), indent=2)
    
    async with Agent(config) as agent:
        prompt = (
            f"You are checking the competitive report for '{competitor_name}'.\n\n"
            f"### Raw Competitor Technical Specs:\n{doc_summary}\n\n"
            f"### Synthesized Competitive Report (Draft):\n{report_json}\n\n"
            "Carefully review the draft report. Perform the following checks:\n"
            "1. Grounding check: Are all mentioned competitor technical constraints actually backed by the raw specs? "
            "If the report contains claims not mentioned in the technical specs, remove them.\n"
            "2. Safety/Data leakage check: Verify there are no confidential customer names or proprietary internal information.\n"
            "3. Structured Validation: Ensure the output follows the required schema format exactly.\n\n"
            "Return the final validated and, if necessary, corrected report matching the requested JSON schema."
        )
        response = await agent.chat(prompt)
        structured_data = await response.structured_output()
        
        if isinstance(structured_data, dict):
            return CompetitorReport(**structured_data)
        elif isinstance(structured_data, CompetitorReport):
            return structured_data
            
        return synthesis_report  # Fallback if checking failed to parse
