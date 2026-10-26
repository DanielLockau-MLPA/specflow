"""Spec MCP server (DR-005): list, draft, run and report on the executable specification.

Run (stdio): uv run python tools/mcp_spec.py
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mcp.server.mcpserver import MCPServer  # noqa: E402

import coverage_report as coveragereport  # noqa: E402
import mcp_shared  # noqa: E402
import specflow_core as core  # noqa: E402
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
    core.require_baseline("model")
    core.require_qa("spec")
    info = core.model_ids()
    if requirement_id not in info:
        raise core.Rejected(f"unknown element ID: {requirement_id}")
    name, text = info[requirement_id]
    return (f"  @{requirement_id}\n  Scenario: {name} (DRAFT)\n    # Requirement: {text}\n"
            f"    Given <precondition>\n    When <action>\n    Then <observable result>\n")


@mcp.tool()
def run() -> list[dict]:
    """Run all scenarios headless; one result per scenario with ID tags, status and duration."""
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "r.json"
        subprocess.run([sys.executable, "-m", "behave", str(core.ROOT / "specs/features"), "-f", "json", "-o", str(out),
                        "--no-summary"], capture_output=True, text=True, cwd=core.ROOT)
        data = json.loads(out.read_text(encoding="utf-8")) if out.exists() else []
    results = []
    for feature in data:
        for el in feature.get("elements", []):
            if el.get("type") == "background":
                continue
            steps = el.get("steps", [])
            results.append({"scenario": el["name"], "location": el["location"],
                            "tags": [t for t in el.get("tags", []) if tracecheck.ID_TAG.match(t)],
                            "status": el.get("status", "untested"),
                            "duration": round(sum(s.get("result", {}).get("duration", 0) for s in steps), 6)})
    return sorted(results, key=lambda r: r["location"])


@mcp.tool()
def coverage(format: str = "json") -> object:
    """Coverage report per level and gate ('json' or 'markdown')."""
    rep = coveragereport.build()
    return rep if format == "json" else coveragereport.markdown(rep)


if __name__ == "__main__":
    mcp.run()
