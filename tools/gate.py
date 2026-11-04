# SPDX-FileCopyrightText: (C) 2026 ML!PA Consulting GmbH
# SPDX-License-Identifier: MIT

"""Gate evaluation: approvals, trace rules, spec results and unreviewed AI-authored content (SR-008, SR-015, SR-045).

A gate opens only when all of these hold (conditions come from approvals/gates.json):
  - every required role has a current valid approval for the unchanged gate scope (approvals.gate_status),
  - the trace rules of the configured stages have no unwaived gap,
  - if "scenarios" is set (G4): the recorded spec run belongs to the current content and every scenario passed,
  - no AI-authored commit in the gate scope is newer than the approvals (it has not been reviewed).

Usage: uv run python tools/gate.py G2 [--run] [--json]     Exit code 1 when the gate is closed.
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import approvals
import exectrace
import specflow_core as core
import specrun
import tracecheck

AI_MARKERS = (f"{core.AI_TRAILER}:", "Co-authored-by: Copilot")
ID_RE = re.compile(r"\b(?:N|UC|SR|DR|SRC|STK)-\d+\b")


def _ai_commits(ws, scope, exclude):
    """AI-authored commits touching the scope that are not ancestors of any commit in `exclude`."""
    args = ["log", "--format=%H%x00%B%x01", "HEAD", *(f"^{c}" for c in exclude), "--", *scope]
    raw = core.git(*args, cwd=ws.root, check=False)
    found = []
    for rec in filter(None, (r.strip("\n") for r in raw.split("\x01"))):
        sha, _, body = rec.partition("\x00")
        if any(m in body for m in AI_MARKERS):
            found.append(sha.strip())
    return found


def _changed_elements(ws, sha, scope):
    """IDs of the elements whose lines a commit changed: the nearest ID declared at or above each changed line."""
    names = core.git("diff-tree", "--no-commit-id", "--name-only", "-r", sha, "--", *scope, cwd=ws.root).split("\n")
    ids = set()
    for name in filter(None, names):
        diff = core.git("diff", "-U0", f"{sha}^", sha, "--", name, cwd=ws.root, check=False)
        if not name.endswith(".sysml"):
            ids.update(ID_RE.findall(diff))
            continue
        text = core.git("show", f"{sha}:{name}", cwd=ws.root, check=False).split("\n")
        for m in re.finditer(r"^@@ -\S+ \+(\d+)(?:,(\d+))?", diff, re.MULTILINE):
            start = int(m.group(1))
            for line in range(start, start + max(int(m.group(2) or 1), 1)):
                for i in range(min(line, len(text)) - 1, -1, -1):
                    hit = ID_RE.search(text[i])
                    if hit:
                        ids.add(hit.group(0))
                        break
    return sorted(ids)


def evaluate(gate, ws=None, run_specs=False):
    ws = ws or core.Workspace()
    cfg = approvals.gates(ws).get(gate)
    status = approvals.gate_status(gate, ws)
    problems = list(status["problems"])
    report = {"gate": gate, "approvals": status}
    if cfg is None:
        return {**report, "open": False, "problems": problems, "trace": None, "scenarios": None, "ai_unreviewed": []}

    stages = tuple(cfg.get("trace", ()))
    trace = tracecheck.evaluate(stages) if stages else {"violations": [], "waived": [], "waivers": [], "invalid_waivers": []}
    report["trace"] = {"stages": list(stages), **{k: trace[k] for k in ("violations", "waived", "waivers", "invalid_waivers")}}
    for v in trace["violations"]:
        problems.append(f"trace gap [{v['stage']}] {v['rule']} {v['element']}: {v['message']}")

    report["scenarios"] = None
    if cfg.get("scenarios"):
        payload = specrun.run(ws) if run_specs else specrun.load(ws)
        why = specrun.freshness(ws, payload)
        if why:
            problems.append(why)
        else:
            # @manual scenarios are verified by humans; the G4 approvers attest them
            manual = [s for s in payload["scenarios"] if s["status"] == "skipped" and s.get("manual")]
            bad = [s for s in payload["scenarios"] if s["status"] != "passed" and s not in manual]
            report["scenarios"] = {"summary": payload["summary"], "not_passed": [f"{s['location']} {s['status']}" for s in bad],
                                   "manual": [s["location"] for s in manual]}
            if bad:
                problems.append(f"{len(bad)} scenario(s) did not pass; first: {bad[0]['location']} ({bad[0]['status']})")
            if cfg.get("railguard"):
                guard = exectrace.report(payload.get("executed_functions"), ws.root)
                report["railguard"] = {k: v for k, v in guard.items() if k != "problems"}
                problems += guard["problems"]

    current = [e["tag"] for e in status["roles"].values() if e["valid"]]
    reviewed = [core.git("rev-parse", f"{t}^{{commit}}", cwd=ws.root) for t in current]
    unreviewed = []
    for sha in _ai_commits(ws, cfg["scope"], reviewed):
        unreviewed.append({"commit": sha[:12], "elements": _changed_elements(ws, sha, cfg["scope"])})
    report["ai_unreviewed"] = unreviewed
    if unreviewed:
        names = sorted({e for u in unreviewed for e in u["elements"]})
        problems.append("unreviewed AI-authored content in the gate scope"
                        + (f": {', '.join(names)}" if names else f" (commits {', '.join(u['commit'] for u in unreviewed)})"))
    report["problems"] = problems
    report["open"] = not problems
    return report


def main(argv):
    gate = next((a for a in argv if not a.startswith("--")), None)
    if not gate:
        print(__doc__)
        return 2
    rep = evaluate(gate, run_specs="--run" in argv)
    if "--json" in argv:
        print(json.dumps(rep, indent=2, sort_keys=True))
    else:
        print(f"{gate}: {'OPEN' if rep['open'] else 'CLOSED'}")
        for p in rep["problems"]:
            print(f"  - {p}")
        if rep.get("railguard"):
            print("\n".join(exectrace.describe(rep["railguard"])))
    return 0 if rep["open"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
