"""Function execution trace for the railguard check (SR-018, DR-036, DR-037).

Importing this module starts a collector when SPECFLOW_TRACE_DIR is set (the spec run sets it). The collector uses
sys.monitoring (standard library) to note every function of tools/ that is entered, in this process and in every
subprocess that imports it, and writes one JSON file per process into the trace directory at exit.
`inventory` lists all functions of the implementation by static analysis; `report` compares it with the merged trace
and the reviewed allowlist (specs/railguard_allowlist.json).

Usage: uv run python tools/exectrace.py report TRACE_DIR [--json]     Exit code 1 when functions were not executed.
"""
import ast
import atexit
import json
import os
import sys
from pathlib import Path

CODE_DIR = Path(__file__).resolve().parent
ALLOWLIST = "specs/railguard_allowlist.json"
TOOL_ID = 3
_seen = set()


def _key(path, qualname):
    return f"{Path(path).resolve().relative_to(CODE_DIR.parent).as_posix()}:{qualname}"


def start(trace_dir):
    mon = sys.monitoring
    mon.use_tool_id(TOOL_ID, "specflow-exectrace")
    prefix = str(CODE_DIR) + os.sep

    def on_start(code, _offset):
        # one event per code object is enough; the location is switched off afterwards
        if code.co_filename.startswith(prefix) and not code.co_name.startswith("<"):
            _seen.add(_key(code.co_filename, code.co_qualname))
        return mon.DISABLE

    mon.register_callback(TOOL_ID, mon.events.PY_START, on_start)
    mon.set_events(TOOL_ID, mon.events.PY_START)

    def flush():
        mon.set_events(TOOL_ID, 0)
        _seen.update(_key(__file__, n) for n in ("start", "start.<locals>.on_start", "start.<locals>.flush"))
        Path(trace_dir).mkdir(parents=True, exist_ok=True)
        (Path(trace_dir) / f"{os.getpid()}.json").write_text(json.dumps(sorted(_seen)), encoding="utf-8")

    atexit.register(flush)


def inventory():
    """All functions of the implementation as '<file>:<qualified name>' keys."""
    found = set()
    for path in sorted(CODE_DIR.rglob("*.py")):
        if "node_modules" in path.parts:
            continue
        found.update(_walk(ast.parse(path.read_text(encoding="utf-8")), path, ""))
    return found


def _walk(node, path, prefix):
    for child in ast.iter_child_nodes(node):
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
            name = prefix + child.name
            yield _key(path, name)
            yield from _walk(child, path, name + ".<locals>.")
        elif isinstance(child, ast.ClassDef):
            yield from _walk(child, path, prefix + child.name + ".")
        else:
            yield from _walk(child, path, prefix)


def merge(trace_dir):
    """Union of the functions recorded by all processes; None when no process recorded anything."""
    files = sorted(Path(trace_dir).glob("*.json")) if Path(trace_dir).is_dir() else []
    if not files:
        return None
    return sorted({k for f in files for k in json.loads(f.read_text(encoding="utf-8"))})


def load_allowlist(root):
    """(valid entries {function: reason}, problems); an entry without a reason is refused."""
    f = Path(root) / ALLOWLIST
    if not f.exists():
        return {}, []
    entries, problems = {}, []
    for e in json.loads(f.read_text(encoding="utf-8")).get("entries", []):
        fn, reason = e.get("function", ""), str(e.get("reason", "")).strip()
        if reason:
            entries[fn] = reason
        else:
            problems.append(f"railguard allowlist entry without a reason: {fn or '(no function)'}")
    return entries, problems


def report(executed, root, functions=None):
    """Compare the implementation inventory with the executed functions (None = nothing was traced)."""
    functions = inventory() if functions is None else set(functions)
    allowed, problems = load_allowlist(root)
    if executed is None:
        return {"traced": False, "unexecuted": [], "allowlisted": [], "stale_allowlist": [], "problems":
                ["no execution trace recorded; run the specification with tracing enabled", *problems]}
    done = set(executed)
    unexecuted = sorted(functions - done - set(allowed))
    problems += [f"function never executed by a scenario: {k}" for k in unexecuted]
    return {"traced": True, "functions": len(functions), "executed": len(functions & done),
            "unexecuted": unexecuted, "allowlisted": sorted(set(allowed) & functions - done),
            "stale_allowlist": sorted(set(allowed) - functions), "problems": problems}


def main(argv):
    if len(argv) < 2 or argv[0] != "report":
        print(__doc__)
        return 2
    rep = report(merge(argv[1]), Path(os.environ.get("SPECFLOW_ROOT", CODE_DIR.parent)))
    print(json.dumps(rep, indent=2, sort_keys=True) if "--json" in argv else "\n".join(rep["problems"]) or "OK")
    return 1 if rep["problems"] else 0


if os.environ.get("SPECFLOW_TRACE_DIR"):
    start(os.environ["SPECFLOW_TRACE_DIR"])

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
