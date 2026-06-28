from dotenv import load_dotenv
from google.antigravity import LocalAgentConfig, types
from google.antigravity.models import (
    ModelTarget, ModelType, GeminiAPIEndpoint, GeminiModelOptions, ThinkingLevel,
)

# Load environment variables
load_dotenv()

# Default model, kept consistent across agents (incl. the bring-your-own-key live
# path); agents are specialized below via reasoning effort, tools, and structured
# output — not by swapping model ids. gemini-2.0-flash was retired (shut down
# 2026-06-01), so this targets gemini-3.5-flash, the current GA Flash model. For
# long-term deprecation-proofing you can instead use the alias "gemini-flash-latest".
DEFAULT_MODEL = "gemini-3.5-flash"

# ---------------------------------------------------------------------------
# Personas (system instructions)
# ---------------------------------------------------------------------------
STRATEGY_PERSONA = (
    "You are the Strategy / Research-Planning Agent — the first step of the pipeline.\n"
    "You read the user's OWN internal business context: their messaging pillars, product "
    "roadmap, and solution map / ICP (ideal customer profile). You do NOT analyze the "
    "competitor yet. Instead you turn that context into a focused research brief that "
    "directs the rest of the pipeline:\n"
    "1. Prioritized 'lenses' — the few competitor capabilities most worth scrutinising, "
    "ordered by what matters to this company's strategy and buyers.\n"
    "2. The ICP framing — who the findings should be written for.\n"
    "3. The messaging pillars the final battle card should be anchored in.\n"
    "Output a concise, structured brief. Set the research agenda; let the later agents execute it."
)

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
    "3. Absolute confidentiality: Ensure no proprietary ActivTrak data or internal customer IP is exposed.\n"
    "4. Professional tone: The output must be objective, factual, and legally defensible.\n"
    "If any part of the synthesis fails these checks, correct it or call out the specific correction needed."
)

# ---------------------------------------------------------------------------
# Per-agent specialization. Each agent is a distinct module with a real,
# role-appropriate config: reasoning effort (ThinkingLevel), which tools it can
# reach, and whether it emits a validated schema. `accent`/`specialty`/`capability`
# drive the run-timeline UI (surfaced via the SSE "pipeline" manifest).
# ---------------------------------------------------------------------------
AGENT_SPECS = {
    "strategy": {
        "label": "Strategy", "persona": STRATEGY_PERSONA,
        "specialty": "Research planning from your context",
        "capability": "internal knowledge", "thinking": ThinkingLevel.HIGH,
        "accent": "amber", "star": False,
    },
    "discovery": {
        "label": "Discovery", "persona": DISCOVERY_PERSONA,
        "specialty": "Documentation ingestion",
        "capability": "MCP doc tools", "thinking": ThinkingLevel.LOW,
        "accent": "blue", "star": False,
    },
    "analysis": {
        "label": "Technical Analysis", "persona": ANALYSIS_PERSONA,
        "specialty": "Claim-vs-reality reasoning",
        "capability": "deep reasoning", "thinking": ThinkingLevel.HIGH,
        "accent": "indigo", "star": True,
    },
    "synthesis": {
        "label": "Synthesis", "persona": SYNTHESIS_PERSONA,
        "specialty": "Battle-card synthesis",
        "capability": "structured schema", "thinking": ThinkingLevel.MEDIUM,
        "accent": "teal", "star": False,
    },
    "checking": {
        "label": "Fact-Checking", "persona": CHECKING_PERSONA,
        "specialty": "Source-grounding QC",
        "capability": "grounding QC", "thinking": ThinkingLevel.HIGH,
        "accent": "green", "star": False,
    },
}

AGENT_ORDER = ["strategy", "discovery", "analysis", "synthesis", "checking"]


def agent_manifest() -> list:
    """Public, secret-free metadata for the frontend run-timeline (the four
    specialized agents, in order). Reasoning level reflects each agent's real
    ThinkingLevel config."""
    return [
        {
            "agent": key,
            "label": s["label"],
            "specialty": s["specialty"],
            "capability": s["capability"],
            "thinking": s["thinking"].value,   # 'low' | 'medium' | 'high'
            "model": DEFAULT_MODEL,
            "accent": s["accent"],
            "star": s["star"],
        }
        for key, s in ((k, AGENT_SPECS[k]) for k in AGENT_ORDER)
    ]


def get_agent_config(persona_type: str, tools: list = None, response_schema=None,
                     mcp_servers: list = None, api_key: str = None) -> LocalAgentConfig:
    """Build a LocalAgentConfig specialized for one agent.

    The agent's reasoning effort comes from its `ThinkingLevel` (the ★ analysis
    and QC agents think harder than discovery). `api_key`, when provided, is the
    caller's bring-your-own-key — used only for this run, never stored or logged.
    """
    spec = AGENT_SPECS.get(persona_type)
    instructions = spec["persona"] if spec else "You are a helpful assistant."
    thinking = spec["thinking"] if spec else ThinkingLevel.MEDIUM

    # A specialized model target: same base model, role-specific reasoning effort.
    endpoint = GeminiAPIEndpoint(
        api_key=api_key,
        options=GeminiModelOptions(thinking_level=thinking),
    )
    target = ModelTarget(name=DEFAULT_MODEL, types=[ModelType.TEXT], endpoint=endpoint)

    return LocalAgentConfig(
        model=target,
        api_key=api_key,
        system_instructions=instructions,
        tools=tools or [],
        mcp_servers=mcp_servers or [],
        response_schema=response_schema,
        capabilities=types.CapabilitiesConfig(enable_subagents=True),
    )
