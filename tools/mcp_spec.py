"""Spec MCP server (DR-005): list, draft, run and report on the executable specification.

Run (stdio): uv run python tools/mcp_spec.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mcp.server.mcpserver import MCPServer  # noqa: E402

import coverage_report as coveragereport  # noqa: E402
import mcp_shared  # noqa: E402
import specflow_core as core  # noqa: E402
import specrun  # noqa: E402
import tracecheck  # noqa: E402

mcp = MCPServer("spec-mcp", instructions="Operations on the executable specification. Scenarios must carry model ID tags.")
mcp_shared.register_common(mcp)
mcp_shared.register_prompts(mcp)


@mcp.tool()
def list_specs() -> list[dict]:
    """List scenarios with their file, line and ID tags."""
    return tracecheck.load_scenarios()


@mcp.tool()
def draft_scenarios(requirement_id: str) -> str:
    """Draft a Gherkin skeleton for a requirement; needs an approved model baseline and a recorded spec Q&A."""
    core.require_preconditions("spec", "model")
    info = core.model_ids()
    if requirement_id not in info:
        raise core.Rejected(f"unknown element ID: {requirement_id}")
    name, text = info[requirement_id]
    return (f"  @{requirement_id}\n  Scenario: {name} (DRAFT)\n    # Requirement: {text}\n"
            f"    Given <precondition>\n    When <action>\n    Then <observable result>\n")


@mcp.tool()
def run() -> list[dict]:
    """Run all scenarios headless; one result per scenario with ID tags, status and duration. The run is recorded as gate evidence."""
    return specrun.run(core.Workspace())["scenarios"]


@mcp.tool()
def coverage(format: str = "json") -> object:
    """Coverage report per level and gate ('json' or 'markdown')."""
    rep = coveragereport.build()
    return rep if format == "json" else coveragereport.markdown(rep)


if __name__ == "__main__":
    mcp.run()
