"""Run the executable specification headless and keep the result as gate evidence (SR-006, DR-007).

`run` executes behave on specs/features, returns one entry per scenario (ID tags, status, duration) and records the
run in .specflow/results/last_run.json together with the repository head and the content fingerprint, so a gate can
tell whether the results belong to the current content.

Usage: uv run python tools/specrun.py [--json]      Exit code 1 when any scenario fails or errors.
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import approvals
import specflow_core as core
import tracecheck

RESULT_SCOPE = ("model/", "specs/")


def result_file(ws):
    return ws.root / ".specflow/results/last_run.json"


def _status_counts(scenarios):
    counts = {}
    for s in scenarios:
        counts[s["status"]] = counts.get(s["status"], 0) + 1
    return dict(sorted(counts.items()))


def run_behave(ws):
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "r.json"
        subprocess.run([sys.executable, "-m", "behave", "specs/features", "-f", "json", "-o", str(out), "--no-summary"],
                       capture_output=True, text=True, cwd=ws.root, env={**os.environ, "SPECFLOW_ROOT": str(ws.root)}, check=False)
        data = json.loads(out.read_text(encoding="utf-8")) if out.exists() else []
    results = []
    for feature in data:
        for el in feature.get("elements", []):
            if el.get("type") == "background":
                continue
            steps = el.get("steps", [])
            failed = next((s for s in steps if s.get("result", {}).get("status") in ("failed", "error")), None)
            results.append({
                "scenario": el["name"], "location": el["location"],
                "tags": [t for t in el.get("tags", []) if tracecheck.ID_TAG.match(t)],
                "status": el.get("status", "untested"),
                "manual": "manual" in el.get("tags", []),
                "duration": round(sum(s.get("result", {}).get("duration", 0) for s in steps), 6),
                "detail": "\n".join(failed["result"].get("error_message", []))[:600] if failed else ""})
    return sorted(results, key=lambda r: r["location"])


def record(ws, scenarios):
    """Store a run as evidence for the current content."""
    head = core.git("rev-parse", "HEAD", cwd=ws.root)
    payload = {"head": head, "fingerprint": approvals.fingerprint(ws, head, RESULT_SCOPE),
               "summary": _status_counts(scenarios), "scenarios": scenarios}
    f = result_file(ws)
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return payload


def run(ws=None):
    ws = ws or core.Workspace()
    return record(ws, run_behave(ws))


def load(ws):
    f = result_file(ws)
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else None


def freshness(ws, payload):
    """Why recorded results do not apply to the current content, or None when they do."""
    if payload is None:
        return "no spec run recorded; run the specification first"
    head = core.git("rev-parse", "HEAD", cwd=ws.root)
    if payload["fingerprint"] != approvals.fingerprint(ws, head, RESULT_SCOPE):
        return "recorded spec results belong to different content; run the specification again"
    dirty = [p for p in (core.git("diff", "--name-only", "HEAD", "--", *RESULT_SCOPE, cwd=ws.root).split("\n")) if p]
    if dirty:
        return "model or specs have uncommitted changes since the recorded run"
    return None


def main(argv):
    ws = core.Workspace()
    payload = run(ws)
    if "--json" in argv:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        for s in payload["scenarios"]:
            print(f"{s['status']:8} {s['location']}  {s['scenario']}")
        print(payload["summary"])
    bad = [s for s in payload["scenarios"] if s["status"] not in ("passed", "skipped")]
    return 1 if bad or not payload["scenarios"] else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
