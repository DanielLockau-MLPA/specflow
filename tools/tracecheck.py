"""Trace and coverage check across needs, use cases, requirements, design elements and scenarios.

Prototype of the trace service (SR-013, SR-014, SR-015, DR-009). Reads the SysML
text with the lightweight reader of tools/arch.py and the specification with
behave's Gherkin parser. Output is deterministic: sorted, no timestamps.

Usage:
    python tools/tracecheck.py check [--stage needs|model|spec|refs|all] [--json]
Stage refs (not part of "all") reports dangling links and links whose target changed since a gate approval.
Exit code 1 when unwaived violations exist.
Waivers are signed tags waiver/<rule>/<element> (see tools/waivers.py). A waiver without rationale, human signer
with a registered key, or a future expiry is invalid and ignored.
"""
import argparse
import hashlib
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from arch import architecture, data_root, ids_and_names, read_model, trace_links

LEVELS = {"N": "need", "UC": "use case", "SR": "requirement (L1)", "DR": "requirement (L2)"}  # sources and stakeholders are not verified by scenarios
ID_TAG = re.compile(r"^[A-Z]{1,3}-\d+$")
STAGES = ("needs", "model", "spec")


def prefix(eid):
    return eid.split("-")[0]


def load_model():
    model = read_model()
    name_to_id, id_info = ids_and_names(model)
    links = trace_links(model, name_to_id)
    _defs, _usages, _conns, sat = architecture(model)
    allocated = {name_to_id[s[0]] for s in sat if s[0] in name_to_id}
    return id_info, links, allocated


def load_scenarios():
    from behave.parser import parse_file

    scenarios = []
    for f in sorted((data_root() / "specs/features").glob("*.feature")):
        feature = parse_file(str(f))
        for sc in feature.scenarios:
            tags = sorted({str(t) for t in sc.effective_tags})
            scenarios.append({"file": f.name, "line": sc.line, "name": sc.name, "tags": tags})
    return scenarios


def reaches_source(start, links):
    """True if a source (SRC) is reachable from `start` along covers, derives and cites links (sources are cited at the highest level)."""
    step = defaultdict(set)
    for a, verb, b in links:
        if verb in ("covers", "derives", "cites"):
            step[a].add(b)
    seen, todo = set(), [start]
    while todo:
        for t in step[todo.pop()]:
            if prefix(t) == "SRC":
                return True
            if t not in seen:
                seen.add(t)
                todo.append(t)
    return False


def check(stage, id_info, links, allocated, scenarios):
    v = []

    def add(rule, element, message):
        v.append({"stage": stage, "rule": rule, "element": element, "message": message})

    ids = sorted(id_info)
    out = defaultdict(set)
    for a, verb, b in links:
        out[(a, verb)].add(b)
    if stage == "needs":
        covered = {b for a, verb, b in links if verb == "covers"}
        for i in ids:
            if prefix(i) == "N" and i not in covered:
                add("need-covered", i, "no use case covers this need")
            if prefix(i) == "N" and not any(prefix(t) == "SRC" for t in out[(i, "cites")]):
                add("need-sourced", i, "this need cites no requirement source")
            if prefix(i) == "SRC":
                if not any(prefix(t) == "STK" for t in out[(i, "raisedBy")]):
                    add("source-stakeholder", i, "this requirement source names no stakeholder")
                if not any(b == i for a, verb, b in links if verb == "cites"):
                    add("source-cited", i, "no need cites this requirement source")
    elif stage == "model":
        for i in ids:
            p = prefix(i)
            if p == "UC" and not out[(i, "exercises")]:
                add("usecase-exercises", i, "use case exercises no requirement")
            if p == "SR" and not any(prefix(t) == "N" for t in out[(i, "derives")]):
                add("l1-derives-need", i, "L1 requirement derives from no need")
            if p == "DR":
                if not any(prefix(t) == "SR" for t in out[(i, "derives")]):
                    add("l2-derives-l1", i, "L2 requirement derives from no L1 requirement")
                if i not in allocated:
                    add("l2-allocated", i, "L2 requirement is allocated to no design element")
        for i in ids:
            if prefix(i) in ("UC", "SR", "DR") and not reaches_source(i, links):
                add("source-traceable", i, "no requirement source is reachable through covers/derives/cites links")
        for a, verb, b in links:
            for x in (a, b):
                if x not in id_info:
                    add("link-target-exists", x, f"link '{a} {verb} {b}' refers to an unknown ID")
    else:
        verified = defaultdict(list)
        for sc in scenarios:
            id_tags = [t for t in sc["tags"] if ID_TAG.match(t)]
            where = f"{sc['file']}:{sc['line']}"
            if not id_tags:
                add("scenario-tagged", where, f"scenario '{sc['name']}' has no ID tag")
            for t in id_tags:
                if t not in id_info:
                    add("tag-valid", t, f"scenario '{sc['name']}' ({where}) is tagged with an unknown ID")
                verified[t].append(where)
        for i in ids:
            if prefix(i) in ("SR", "DR") and i not in verified:
                add("requirement-verified", i, "no scenario verifies this requirement")
    return v


def element_hash(name, doc):
    return hashlib.sha256(f"{name}\n{doc}".encode()).hexdigest()


def reference_findings(ws=None):
    """Stage "refs": dangling links (a link names an element that is not defined) and stale links (the target's
    content differs from its content at every commit approved by a gate)."""
    import approvals
    import specflow_core as core
    ws = ws or core.Workspace()
    v = []
    model = read_model()
    _n, id_info = ids_and_names(model)
    labels = [m for src in model.values() for m in re.findall(r"dependency\s+'([^']*)'", src)]
    link_ids = sorted({i for label in labels for i in re.findall(r"\b[A-Z]{1,3}-\d+\b", label)})
    for i in link_ids:
        if i not in id_info:
            v.append({"stage": "refs", "rule": "link-dangling", "element": i,
                      "message": "a link refers to an element that is not defined"})
    commits = set()
    for gate in approvals.gates(ws):
        for entry in approvals.gate_status(gate, ws)["roles"].values():
            if entry["valid"]:
                commits.add(core.git("rev-parse", f"{entry['tag']}^{{commit}}", cwd=ws.root))
    approved = {}
    for commit in sorted(commits):
        files = core.git("ls-tree", "-r", "--name-only", commit, "--", "model", cwd=ws.root).split("\n")
        old = {f: core.git("show", f"{commit}:{f}", cwd=ws.root) for f in files if f.endswith(".sysml")}
        for eid, (name, doc) in ids_and_names(old)[1].items():
            approved.setdefault(eid, set()).add(element_hash(name, doc))
    for i in link_ids:
        if i in id_info and i in approved and element_hash(*id_info[i]) not in approved[i]:
            v.append({"stage": "refs", "rule": "link-stale", "element": i,
                      "message": "the link target changed since it was approved"})
    return v


def graph(id_info=None, links=None, scenarios=None):
    """Trace graph as sorted nodes and edges: model links plus scenario-to-ID tags (scenario nodes are file:line)."""
    if id_info is None:
        id_info, links, _allocated = load_model()
        scenarios = load_scenarios()
    edges = {(a, verb, b) for a, verb, b in links}
    nodes = set(id_info)
    for sc in scenarios:
        where = f"{sc['file']}:{sc['line']}"
        nodes.add(where)
        edges.update((where, "verifies", t) for t in sc["tags"] if ID_TAG.match(t))
    return {"nodes": sorted(nodes), "edges": [list(e) for e in sorted(edges)]}


def graph_json():
    return json.dumps(graph(), indent=2, sort_keys=True)


def query(source, target):
    """Elements connected to `source` (following links in both directions) that are `target` (an ID, a prefix such as
    N, or "scenario"), each with the shortest connecting path."""
    g = graph()
    adj = defaultdict(set)
    for a, _verb, b in g["edges"]:
        adj[a].add(b)
        adj[b].add(a)
    if source == "scenario":
        starts = [n for n in g["nodes"] if ".feature:" in n]
    else:
        starts = [source] if source in g["nodes"] else []
    paths = {}
    for start in starts:
        seen, queue = {start: [start]}, [start]
        for node in queue:
            for nxt in sorted(adj[node]):
                if nxt not in seen:
                    seen[nxt] = [*seen[node], nxt]
                    queue.append(nxt)
        for node, path in seen.items():
            hit = ".feature:" in node if target == "scenario" else (node == target or prefix(node) == target)
            if hit and node != start:
                paths.setdefault(node, path)
    return {"from": source, "to": target, "connected": sorted(paths), "paths": dict(sorted(paths.items()))}


def summary(id_info, scenarios):
    verified = {t for sc in scenarios for t in sc["tags"] if ID_TAG.match(t)}
    rows = {}
    for p, label in LEVELS.items():
        members = [i for i in id_info if prefix(i) == p]
        rows[label] = {"total": len(members), "with_scenario": sum(1 for i in members if i in verified)}
    rows["scenarios"] = {"total": len(scenarios), "tagged": sum(1 for s in scenarios if any(ID_TAG.match(t) for t in s["tags"]))}
    return rows


def load_waivers():
    import waivers
    return waivers.load()


def evaluate(stages):
    id_info, links, allocated = load_model()
    scenarios = load_scenarios()
    violations = [x for s in stages if s != "refs" for x in check(s, id_info, links, allocated, scenarios)]
    if "refs" in stages:
        violations += reference_findings()
    valid_w, invalid_w = load_waivers()
    import waivers
    waived_keys = {(w["rule"], w["element"]) for w in valid_w}

    def is_waived(x):
        return (x["rule"], waivers.element_key(x["element"])) in waived_keys

    open_v = [x for x in violations if not is_waived(x)]
    violations.sort(key=lambda x: (x["stage"], x["rule"], x["element"]))
    return {
        "summary": summary(id_info, scenarios),
        "violations": sorted(open_v, key=lambda x: (x["stage"], x["rule"], x["element"])),
        "waived": [x for x in violations if is_waived(x)],
        "waivers": sorted(valid_w, key=lambda w: (w["rule"], w["element"])),
        "invalid_waivers": invalid_w,
    }


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("command", choices=["check"])
    ap.add_argument("--stage", choices=[*STAGES, "refs", "all"], default="all")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    stages = STAGES if args.stage == "all" else (args.stage,)
    result = evaluate(stages)
    open_v = result["violations"]
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        for level, row in result["summary"].items():
            print(f"{level:18} " + ", ".join(f"{k}={v}" for k, v in row.items()))
        for x in open_v:
            print(f"VIOLATION [{x['stage']}] {x['rule']} {x['element']}: {x['message']}")
        for x in result["waived"]:
            print(f"WAIVED    [{x['stage']}] {x['rule']} {x['element']}")
        for w in result["invalid_waivers"]:
            print(f"INVALID WAIVER ignored: {w}")
        print("OK" if not open_v else f"{len(open_v)} violation(s)")
    return 1 if open_v else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
