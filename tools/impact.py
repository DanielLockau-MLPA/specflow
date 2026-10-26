"""Impact analysis for a change to a model element (SR-010, DR-017).

Upstream: elements the element derives from, covers or exercises (transitively). Downstream: elements that
derive from, cover or exercise it (transitively), allocated design parts, and the scenarios tagged with the
element or any downstream element. Gates whose scope contains the element's file need re-approval.

Usage: uv run python tools/impact.py SR-004 [--json]
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import approvals  # noqa: E402
import specflow_core as core  # noqa: E402
import tracecheck  # noqa: E402


def _closure(start, edges):
    seen, todo = set(), [start]
    while todo:
        for nxt in edges.get(todo.pop(), ()):
            if nxt not in seen:
                seen.add(nxt)
                todo.append(nxt)
    return seen


def element_file(ws, element):
    for f in sorted((ws.root / "model").glob("*.sysml")):
        if re.search(rf"<'{re.escape(element)}'", f.read_text(encoding="utf-8")):
            return f.relative_to(ws.root).as_posix()
    return None


def analyse(element, ws=None):
    ws = ws or core.Workspace()
    info, links, _allocated = tracecheck.load_model()
    if element not in info:
        raise core.Rejected(f"unknown element ID: {element}")
    up, down = {}, {}
    for a, _verb, b in links:
        up.setdefault(a, set()).add(b)
        down.setdefault(b, set()).add(a)
    upstream = sorted(_closure(element, up))
    downstream = sorted(_closure(element, down))
    scenarios = tracecheck.load_scenarios()
    affected = {element, *downstream}
    hit = sorted(f"{s['file']}:{s['line']} {s['name']}" for s in scenarios if affected & set(s["tags"]))
    path = element_file(ws, element)
    gates = sorted(g for g, c in approvals.gates(ws).items()
                   if path and any(path == s or path.startswith(s) for s in c["scope"]))
    return {"element": element, "file": path, "upstream": upstream, "downstream": downstream,
            "scenarios": hit, "gates_needing_reapproval": gates}


def main(argv):
    if not argv:
        print(__doc__)
        return 2
    try:
        rep = analyse(argv[0])
    except core.Rejected as e:
        print(e, file=sys.stderr)
        return 1
    if "--json" in argv:
        print(json.dumps(rep, indent=2, sort_keys=True))
    else:
        print(f"{rep['element']} ({rep['file']})")
        for k in ("upstream", "downstream", "scenarios", "gates_needing_reapproval"):
            print(f"  {k}: {', '.join(rep[k]) or '-'}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
