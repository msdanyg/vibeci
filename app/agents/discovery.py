"""
Discovery Agent — documentation ingestion using the MCP server tools.

This agent uses the `ci-doc-tools` MCP server (app/mcp_server.py) via the
Antigravity SDK's native `mcp_servers` / `McpStdioServer` integration to:
  1. Fetch raw technical documentation for a competitor via `fetch_competitor_docs`.
  2. The MCP server also exposes `compare_claims_to_docs` for downstream use.

By routing document fetching through MCP, the fetch logic is independently
testable and replaceable without changing the agent orchestration layer —
a clean separation of concerns between tool execution and agent reasoning.
"""

import sys
from google.antigravity import Agent
from google.antigravity.types import McpStdioServer
from app.agents.config import get_agent_config

# ---------------------------------------------------------------------------
# MCP server connection: launch app/mcp_server.py as a subprocess over stdio.
# The Antigravity SDK starts and stops this process around each agent context.
# ---------------------------------------------------------------------------
CI_DOC_MCP_SERVER = McpStdioServer(
    name="ci-doc-tools",
    # Run the MCP server using the same Python interpreter as the current process
    # so the venv and all packages (httpx, mcp) are available.
    command=sys.executable,
    args=["-m", "app.mcp_server"],
)


async def run_discovery_agent(competitor_name: str, doc_url: str = None) -> str:
    """Orchestrate the Discovery Agent using MCP tools for document ingestion.

    The agent is configured with the ci-doc-tools MCP server. At runtime the
    SDK spawns the server subprocess and exposes its tools to the Gemini model:
      - fetch_competitor_docs  — retrieves raw technical specs (live or mock).
      - compare_claims_to_docs — keyword-level pre-screen (used by analysis agent).

    Args:
        competitor_name: Display name of the competitor (e.g. "Teramind").
        doc_url:         Optional URL to the competitor's API docs or KB portal.

    Returns:
        A structured markdown summary of the competitor's raw technical specs.
    """
    # get_agent_config returns a LocalAgentConfig; we extend it with the MCP server
    config = get_agent_config("discovery", mcp_servers=[CI_DOC_MCP_SERVER])

    async with Agent(config) as agent:
        prompt = (
            f"You are ingesting technical documentation for the competitor: '{competitor_name}'.\n\n"
            f"Step 1: Call the `fetch_competitor_docs` tool with "
            f"competitor_name='{competitor_name}' and doc_url='{doc_url or ''}'.\n\n"
            "Step 2: Read the returned documentation carefully. Clean it up and "
            "extract API structures, feature constraints, rate limits, latency "
            "numbers, and any documented technical limitations. "
            "Output a clean, structured markdown document summarising the raw "
            "technical specifications. Do not add interpretation — facts only."
        )
        response = await agent.chat(prompt)
        return await response.text()
