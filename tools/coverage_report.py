"""Coverage report along need, use case, requirement, design element and scenario (SR-005, DR-011).

Produces JSON or Markdown with stable ordering (sorted, no timestamps), a summary per level and per gate,
and a list of every gap. Gate rows cover the trace rules only; spec run results are not included yet.

Usage:
    python tools/coverage_report.py [--format json|markdown] [--out FILE]
Exit code 1 when any gap is unwaived.
"""
import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from arch import architecture, ids_and_names, read_model  # noqa: E402
from tracecheck import ID_TAG, evaluate, load_model, load_scenarios, prefix  # noqa: E402

GATES = {"G1": ("needs",), "G2": ("needs", "model"), "G3": ("needs", "model", "spec"), "G4": ("needs", "model", "spec")}


def build():
    id_info, links, allocated = load_model()
    scenarios = load_scenarios()
    model = read_model()
    name_to_id, _ = ids_and_names(model)
    _defs, usages, _conns, sat = architecture(model)

    per_part = defaultdict(set)
    for req, by in sat:
        part = by.split(".")[-1]
        if req in name_to_id and part in usages:
            per_part[part].add(name_to_id[req])

    verified = {t for sc in scenarios for t in sc["tags"] if ID_TAG.match(t)}
    covered_needs = {b for _a, verb, b in links if verb == "covers"}
    exercising = {a for a, verb, _b in links if verb == "exercises"}

    def row(level, members, ok):
        ok_members = [m for m in members if ok(m)]
        return {"level": level, "total": len(members), "covered": len(ok_members),
                "gaps": sorted(m for m in members if not ok(m))}

    ids = sorted(id_info)
    parts = sorted(u for u, (_t, blk) in usages.items() if blk == "Toolchain")
    levels = [
        row("need (covered by a use case)", [i for i in ids if prefix(i) == "N"], covered_needs.__contains__),
        row("use case (exercises a requirement)", [i for i in ids if prefix(i) == "UC"], exercising.__contains__),
        row("L1 requirement (verified by a scenario)", [i for i in ids if prefix(i) == "SR"], verified.__contains__),
        row("L2 requirement (verified by a scenario)", [i for i in ids if prefix(i) == "DR"], verified.__contains__),
        row("L2 requirement (allocated to a design element)", [i for i in ids if prefix(i) == "DR"], allocated.__contains__),
        row("design element (satisfies a requirement)", parts, lambda p: bool(per_part[p])),
    ]
    sc_names = {f"{s['file']}:{s['line']}": s for s in scenarios}
    levels.append(row("scenario (references an existing ID)", sorted(sc_names),
                      lambda k: any(t in id_info for t in sc_names[k]["tags"])))

    gates = {}
    for gate, stages in GATES.items():
        res = evaluate(stages)
        gates[gate] = {"stages": list(stages), "open_violations": len(res["violations"]),
                       "waived": len(res["waived"]), "trace_status": "ok" if not res["violations"] else "gaps"}
    full = evaluate(("needs", "model", "spec"))
    return {"levels": levels, "gates": gates, "violations": full["violations"], "waivers": full["waivers"],
            "invalid_waivers": full["invalid_waivers"]}


def markdown(rep):
    o = ["# Coverage report", "", "## Levels", "", "| Level | Covered | Total | Gaps |", "|---|---:|---:|---|"]
    for r in rep["levels"]:
        o.append(f"| {r['level']} | {r['covered']} | {r['total']} | {', '.join(r['gaps']) or '-'} |")
    o += ["", "## Gates (trace rules only)", "", "| Gate | Stages | Open violations | Waived | Trace status |", "|---|---|---:|---:|---|"]
    for g, r in rep["gates"].items():
        o.append(f"| {g} | {', '.join(r['stages'])} | {r['open_violations']} | {r['waived']} | {r['trace_status']} |")
    o += ["", "## Gaps", ""]
    o += [f"- [{v['stage']}] `{v['rule']}` {v['element']}: {v['message']}" for v in rep["violations"]] or ["None."]
    o += ["", "## Waivers", ""]
    o += [f"- {w['rule']} {w['element']}: {w['rationale']} (approver {w['approver']}, expires {w['expiry']})"
          for w in rep["waivers"]] or ["None."]
    return "\n".join(o) + "\n"


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--format", choices=["json", "markdown"], default="markdown")
    ap.add_argument("--out")
    args = ap.parse_args(argv)
    rep = build()
    text = json.dumps(rep, indent=2, sort_keys=True) + "\n" if args.format == "json" else markdown(rep)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 1 if rep["violations"] else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
