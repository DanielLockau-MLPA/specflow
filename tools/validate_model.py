"""Validate the SysML v2 files in model/ with the sysml-mcp backend (npm sysml-v2-lsp).

All files are parsed first so cross-file references resolve, then each is
validated. Exit code is non-zero on syntax errors or semantic errors.
Warnings about unsatisfied/unverified requirements are expected until the
design and specs exist; they are summarised, not failed.

Usage: uv run python tools/validate_model.py [--verbose]
"""
import asyncio
import glob
import json
import sys
from collections import Counter
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parent.parent
SERVER = ROOT / "tools/node/node_modules/sysml-v2-lsp/dist/server/mcpServer.js"


async def main(verbose: bool) -> int:
    if not SERVER.exists():
        print(f"sysml-mcp not found at {SERVER}; run ./setup.sh --install", file=sys.stderr)
        return 2
    files = sorted(glob.glob(str(ROOT / "model/*.sysml")))
    failed = False
    params = StdioServerParameters(command="node", args=[str(SERVER)])
    async with stdio_client(params) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            docs = {f: Path(f).read_text(encoding="utf-8") for f in files}
            for f, code in docs.items():
                await s.call_tool("parse", {"code": code, "uri": f})
            for f, code in docs.items():
                res = await s.call_tool("validate", {"code": code, "uri": f})
                d = json.loads("".join(c.text for c in res.content))
                name = Path(f).relative_to(ROOT)
                counts = Counter((i["severity"], i["code"]) for i in d["semanticIssues"])
                errors = [i for i in d["semanticIssues"] if i["severity"] == "error"]
                print(f"{name}: valid={d['valid']} syntax_errors={len(d['syntaxErrors'])} "
                      f"semantic_errors={len(errors)}")
                for e in d["syntaxErrors"]:
                    print(f"  SYNTAX {e['line']}:{e['column']} {e['message']}")
                for e in errors:
                    print(f"  ERROR {e['line']}:{e['column']} {e['message']}")
                if verbose:
                    for (sev, code_), n in sorted(counts.items()):
                        print(f"  {sev} {code_}: {n}")
                if d["syntaxErrors"] or errors or not d["valid"]:
                    failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main("--verbose" in sys.argv)))
