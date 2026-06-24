import os
from google.antigravity import LocalAgentConfig, types
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Verify Gemini API key
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    # We will let the SDK try to find it or raise a clear exception.
    # Note: The agent can read it automatically from the environment.
    pass

# Default Model — gemini-2.0-flash is the correct, available model ID
DEFAULT_MODEL = "gemini-2.0-flash"

# System Instructions / Personas for the agents

DISCOVERY_PERSONA = (
    "You are a Discovery and Monitoring Agent for Competitive Intelligence.\n"
    "Your job is to read and ingest the technical documentation provided by the user. "
    "Use the tools at your disposal to read documentation content from URLs or use the fallback tools "
    "if live scraping fails. Clean the text, extract code blocks, API structures, and raw capabilities, "
    "and output a consolidated, clean markdown file summarizing the raw technical specifications. "
    "Focus on accuracy and do not add any interpretation yet."
)

ANALYSIS_PERSONA = (
    "You are the Technical Analysis Agent, the core star of this competitive intelligence platform.\n"
    "Your job is to read the competitor's raw technical documentation (provided by the Discovery Agent), "
    "extract the actual capabilities (endpoints, rate limits, latency, constraints, config options), "
    "and contrast them against:\n"
    "1. The competitor's marketing claims (what they promise on their website).\n"
    "2. The user's own company positioning (provided below).\n\n"
    "Identify critical feature gaps, technical constraints, and differences between claims and reality. "
    "Be precise and factual. Highlight direct gaps (e.g., marketing claims 'instant analytics', but docs reveal "
    "'data updates every 4 hours'). Do not make assumptions not backed by the documentation."
)

SYNTHESIS_PERSONA = (
    "You are the Synthesis Agent.\n"
    "Your job is to take the detailed technical analysis and claim comparisons, and format them into "
    "actionable, high-impact sales battle cards, comparative matrices, and customer-facing elevator pitches.\n"
    "Organize your findings with:\n"
    "- Key Takeaways (The TL;DR for sales reps)\n"
    "- side-by-side marketing claim vs. technical reality table\n"
    "- Competitor strength and weakness checklist\n"
    "- Specific landmines to lay during sales conversations."
)

CHECKING_PERSONA = (
    "You are the Fact-Checking and Quality Control Agent.\n"
    "Your job is to review the generated competitive intelligence output. "
    "Check for the following criteria:\n"
    "1. Source grounding: Every limitation or gap attributed to a competitor must be directly backed by the technical documentation.\n"
    "2. No hallucinations or exaggerations.\n"
    "3. Absolute confidentiality: Ensure no proprietary ActiveTrack data or internal customer IP is exposed.\n"
    "4. Professional tone: The output must be objective, factual, and legally defensible.\n"
    "If any part of the synthesis fails these checks, correct it or call out the specific correction needed."
)

def get_agent_config(persona_type: str, tools: list = None, response_schema=None, mcp_servers: list = None) -> LocalAgentConfig:
    """Helper function to create a LocalAgentConfig with standard settings.
    
    Args:
        persona_type:  One of 'discovery', 'analysis', 'synthesis', 'checking'.
        tools:         Optional list of Python callables to expose as tools.
        response_schema: Optional Pydantic model for structured JSON output.
        mcp_servers:   Optional list of McpStdioServer / McpStreamableHttpServer
                       instances to connect to this agent.
    """
    if persona_type == "discovery":
        instructions = DISCOVERY_PERSONA
    elif persona_type == "analysis":
        instructions = ANALYSIS_PERSONA
    elif persona_type == "synthesis":
        instructions = SYNTHESIS_PERSONA
    elif persona_type == "checking":
        instructions = CHECKING_PERSONA
    else:
        instructions = "You are a helpful assistant."

    return LocalAgentConfig(
        model=DEFAULT_MODEL,
        system_instructions=instructions,
        tools=tools or [],
        mcp_servers=mcp_servers or [],
        response_schema=response_schema,
        capabilities=types.CapabilitiesConfig(
            enable_subagents=True
        )
    )
