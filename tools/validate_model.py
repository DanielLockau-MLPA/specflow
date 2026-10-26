"""Validate the SysML v2 files in model/ with a replaceable parser backend (DR-002).

Findings have one structure regardless of the backend: file, line, column, severity (error|warning|info),
code, message and the nearest preceding element ID. The default backend is sysml-mcp (npm sysml-v2-lsp).
Another backend is selected with SPECFLOW_PARSER_BACKEND="module:function"; the function takes
{path: text} and returns a list of finding dicts (file, line, column, severity, code, message).

Exit code is non-zero on errors. Warnings about unsatisfied/unverified requirements are expected until the
design and specs exist; they are summarised, not failed.

Usage: uv run python tools/validate_model.py [--verbose] [--json]
"""
import asyncio
import glob
import importlib
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = Path(os.environ.get("SPECFLOW_ROOT", ROOT)).resolve()
SERVER = ROOT / "tools/node/node_modules/sysml-v2-lsp/dist/server/mcpServer.js"
ID_DECL = re.compile(r"<'([A-Z]{1,3}-\d+)'?")
REQ_DECL = re.compile(r"requirement\s+<'([A-Z]{1,3}-\d+)'>[^{;]*\{")


async def sysml_mcp_backend(docs):
    """Default backend: parse all files first so cross-file references resolve, then validate each."""
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    if not SERVER.exists():
        raise RuntimeError(f"sysml-mcp not found at {SERVER}; run ./setup.sh --install")
    findings = []
    async with stdio_client(StdioServerParameters(command="node", args=[str(SERVER)])) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            for f, code in docs.items():
                await s.call_tool("parse", {"code": code, "uri": f})
            for f, code in docs.items():
                res = await s.call_tool("validate", {"code": code, "uri": f})
                d = json.loads("".join(c.text for c in res.content))
                for e in d["syntaxErrors"]:
                    findings.append({"file": f, "line": e["line"], "column": e["column"], "severity": "error",
                                     "code": "syntax", "message": e["message"]})
                for e in d["semanticIssues"]:
                    findings.append({"file": f, "line": e["line"], "column": e["column"], "severity": e["severity"],
                                     "code": e["code"], "message": e["message"]})
    return findings


def _backend():
    spec = os.environ.get("SPECFLOW_PARSER_BACKEND")
    if not spec:
        return sysml_mcp_backend
    module, _, func = spec.partition(":")
    return getattr(importlib.import_module(module), func)


def _element_at(text, line):
    """ID of the nearest element declaration at or above the line (empty when none)."""
    found = ""
    for n, row in enumerate(text.splitlines(), 1):
        if n > line:
            break
        m = ID_DECL.search(row)
        if m:
            found = m.group(1)
    return found


def _undocumented_requirements(path, text):
    """Convention check independent of the backend: every identified requirement needs a doc comment."""
    out = []
    for m in REQ_DECL.finditer(text):
        depth, i = 1, m.end()
        while i < len(text) and depth:
            depth += {"{": 1, "}": -1}.get(text[i], 0)
            i += 1
        if not re.search(r"\bdoc\s*/\*", text[m.end():i]):
            line = text.count("\n", 0, m.start()) + 1
            out.append({"file": path, "line": line, "column": 1, "severity": "warning", "code": "requirement-doc",
                        "message": f"Requirement '{m.group(1)}' has no documentation", "element": m.group(1)})
    return out


def collect():
    files = sorted(glob.glob(str(DATA / "model/*.sysml")))
    docs = {f: Path(f).read_text(encoding="utf-8") for f in files}
    result = _backend()(docs)
    findings = asyncio.run(result) if asyncio.iscoroutine(result) else result
    for path, text in docs.items():
        findings += _undocumented_requirements(path, text)
    for f in findings:
        f["element"] = f.get("element") or _element_at(docs.get(f["file"], ""), f["line"])
        f["file"] = str(Path(f["file"]).relative_to(DATA)) if Path(f["file"]).is_absolute() else f["file"]
    return sorted(findings, key=lambda f: (f["file"], f["line"], f["column"], f["code"])), [
        str(Path(p).relative_to(DATA)) for p in files]


def main(argv):
    try:
        findings, files = collect()
    except RuntimeError as e:
        print(e, file=sys.stderr)
        return 2
    errors = [f for f in findings if f["severity"] == "error"]
    if "--json" in argv:
        print(json.dumps({"files": files, "findings": findings}, indent=2, sort_keys=True))
        return 1 if errors else 0
    for name in files:
        own = [f for f in findings if f["file"] == name]
        errs = [f for f in own if f["severity"] == "error"]
        syntax = sum(f["code"] == "syntax" for f in own)
        print(f"{name}: valid={not errs} syntax_errors={syntax} semantic_errors={len(errs) - syntax}")
        for f in errs:
            print(f"  ERROR {f['line']}:{f['column']} {f['message']} [{f['element'] or '-'}]")
        if "--verbose" in argv:
            for (sev, code), c in sorted(Counter((f["severity"], f["code"]) for f in own).items()):
                print(f"  {sev} {code}: {c}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
