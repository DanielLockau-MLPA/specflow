"""Trace and coverage check across needs, use cases, requirements, design elements and scenarios.

Prototype of the trace service (SR-013, SR-014, SR-015, DR-009). Reads the SysML
text with the lightweight reader of tools/arch.py and the specification with
behave's Gherkin parser. Output is deterministic: sorted, no timestamps.

Usage:
    python tools/trace.py check [--stage needs|model|spec|all] [--json]
Exit code 1 when unwaived violations exist.
Waivers (optional): trace/waivers.json, a list of
    {"rule": ..., "element": ..., "rationale": ..., "approver": ..., "expiry": "YYYY-MM-DD"}
A waiver without rationale, human approver or a future expiry is invalid and ignored.
"""
import argparse
import datetime
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from arch import ROOT, architecture, ids_and_names, read_model, trace_links  # noqa: E402

LEVELS = {"N": "need", "UC": "use case", "SR": "requirement (L1)", "DR": "requirement (L2)"}
ID_TAG = re.compile(r"^[A-Z]{1,3}-\d+$")
STAGES = ("needs", "model", "spec")
WAIVERS = ROOT / "trace/waivers.json"
FEATURES = ROOT / "specs/features"


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
    for f in sorted(FEATURES.glob("*.feature")):
        feature = parse_file(str(f))
        for sc in feature.scenarios:
            tags = sorted({str(t) for t in sc.effective_tags})
            scenarios.append({"file": f.name, "line": sc.line, "name": sc.name, "tags": tags})
    return scenarios


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


def summary(id_info, scenarios):
    verified = {t for sc in scenarios for t in sc["tags"] if ID_TAG.match(t)}
    rows = {}
    for p, label in LEVELS.items():
        members = [i for i in id_info if prefix(i) == p]
        rows[label] = {"total": len(members), "with_scenario": sum(1 for i in members if i in verified)}
    rows["scenarios"] = {"total": len(scenarios), "tagged": sum(1 for s in scenarios if any(ID_TAG.match(t) for t in s["tags"]))}
    return rows


def load_waivers():
    if not WAIVERS.exists():
        return [], []
    valid, invalid = [], []
    today = datetime.date.today().isoformat()
    for w in json.loads(WAIVERS.read_text(encoding="utf-8")):
        ok = (w.get("rationale") and w.get("approver") and not str(w["approver"]).lower().startswith("agent")
              and str(w.get("expiry", "")) >= today)
        (valid if ok else invalid).append(w)
    return valid, invalid


def evaluate(stages):
    id_info, links, allocated = load_model()
    scenarios = load_scenarios()
    violations = [x for s in stages for x in check(s, id_info, links, allocated, scenarios)]
    valid_w, invalid_w = load_waivers()
    waived_keys = {(w["rule"], w["element"]) for w in valid_w}
    open_v = [x for x in violations if (x["rule"], x["element"]) not in waived_keys]
    violations.sort(key=lambda x: (x["stage"], x["rule"], x["element"]))
    return {
        "summary": summary(id_info, scenarios),
        "violations": sorted(open_v, key=lambda x: (x["stage"], x["rule"], x["element"])),
        "waived": [x for x in violations if (x["rule"], x["element"]) in waived_keys],
        "waivers": sorted(valid_w, key=lambda w: (w["rule"], w["element"])),
        "invalid_waivers": invalid_w,
    }


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("command", choices=["check"])
    ap.add_argument("--stage", choices=[*STAGES, "all"], default="all")
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
