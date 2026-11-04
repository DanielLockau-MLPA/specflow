# SPDX-FileCopyrightText: (C) 2026 ML!PA Consulting GmbH
# SPDX-License-Identifier: MIT

"""Audit queries and the evidence bundle per gate (SR-030, SR-032, DR-020, DR-031).

Everything is read from git and the recorded spec run, without an MCP client or the agent.

Usage:
    uv run python tools/audit.py GATE approvals|waivers|changes|test-evidence|integrity [--json]
    uv run python tools/audit.py GATE bundle [--out FILE]
Exit code 1 when the queried integrity status is not ok.
"""
import json
import platform
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import approvals
import gate as gatelib
import specflow_core as core
import specrun
import waivers

SUBJECTS = ("approvals", "waivers", "changes", "test-evidence", "integrity")


def _cfg(ws, gate):
    cfg = approvals.gates(ws).get(gate)
    if cfg is None:
        raise core.Rejected(f"gate not configured: {gate}")
    return cfg


def approval_records(gate, ws=None):
    ws = ws or core.Workspace()
    cfg = _cfg(ws, gate)
    out = []
    for role in cfg["roles"]:
        tags = approvals.role_tags(ws, gate, role)
        current = approvals.current_tag(ws, gate, role)[0]
        for rev, name in tags:
            v = approvals.verify_tag(name, ws)
            fmt = "%(taggerdate:iso-strict)%00%(contents)%00%(*objectname)%(objectname)"
            date, msg, _ = (core.git("tag", "--list", f"--format={fmt}", name, cwd=ws.root).split("\x00") + ["", ""])[:3]
            out.append({"gate": gate, "role": role, "revision": rev, "tag": name, "valid": v.ok, "signer": v.signer,
                        "reason": v.reason, "date": date, "message": msg.split("-----BEGIN SSH SIGNATURE-----")[0].strip(),
                        "commit": core.git("rev-parse", f"{name}^{{commit}}", cwd=ws.root),
                        "superseded": name != current})
    return out


def change_records(gate, ws=None):
    """Commits that touched the gate scope after the first approval, with who, when, why and approver."""
    ws = ws or core.Workspace()
    cfg = _cfg(ws, gate)
    refs = core.git("for-each-ref", "--sort=creatordate", "--format=%(objectname)", f"refs/tags/approval/{gate}/", cwd=ws.root).split()
    if not refs:
        return []
    first = core.git("rev-parse", f"{refs[0]}^{{commit}}", cwd=ws.root)
    registered = set(json.loads((ws.root / "approvals/roles.json").read_text(encoding="utf-8")))
    fmt = "%H%x00%an%x00%aI%x00%s%x00%(trailers:key=Change-Reason,valueonly,separator=%x20)%x00%(trailers:key=Approved-By,valueonly,separator=%x20)%x01"
    raw = core.git("log", f"--format={fmt}", "HEAD", f"^{first}", "--", *cfg["scope"], cwd=ws.root, check=False)
    out = []
    for rec in filter(None, (r.strip("\n") for r in raw.split("\x01"))):
        sha, who, when, subject, reason, approver = (rec.split("\x00") + [""] * 6)[:6]
        reason, approver = reason.strip(), approver.strip()
        problems = []
        if not reason:
            problems.append("no reason")
        if not approver:
            problems.append("no approver")
        elif approver not in registered:
            problems.append(f"approver {approver} is not a registered principal")
        elif approver == who:
            problems.append("approver is the author")
        out.append({"commit": sha.strip(), "who": who, "when": when, "subject": subject, "why": reason,
                    "approver": approver, "complete": not problems, "problems": problems})
    return out


def test_evidence(ws):
    payload = specrun.load(ws)
    if payload is None:
        return {"run": None, "requirements": {}}
    by_req = defaultdict(list)
    for s in payload["scenarios"]:
        for t in s["tags"]:
            by_req[t].append({"scenario": s["scenario"], "location": s["location"], "status": s["status"],
                              "duration": s["duration"]})
    return {"run": {"head": payload["head"], "summary": payload["summary"],
                    "current": specrun.freshness(ws, payload) is None},
            "requirements": {k: by_req[k] for k in sorted(by_req)}}


def integrity(gate, ws=None):
    ws = ws or core.Workspace()
    st = approvals.gate_status(gate, ws)
    records = approval_records(gate, ws)
    invalid = [r["tag"] for r in records if not r["valid"] and not r["superseded"]]
    ok = not invalid and not st["drift"] and not any("different scope" in p or "scope changed" in p for p in st["problems"])
    return {"gate": gate, "ok": ok, "invalid_current_approvals": invalid, "drift": st["drift"], "problems": st["problems"]}


def query(gate, subject, ws=None):
    ws = ws or core.Workspace()
    if subject == "approvals":
        return approval_records(gate, ws)
    if subject == "waivers":
        valid, invalid = waivers.load(ws)
        return {"valid": valid, "invalid": invalid}
    if subject == "changes":
        return change_records(gate, ws)
    if subject == "test-evidence":
        return test_evidence(ws)
    if subject == "integrity":
        return integrity(gate, ws)
    raise core.Rejected(f"unknown subject: {subject}; choose one of {', '.join(SUBJECTS)}")


def bundle(gate, ws=None):
    ws = ws or core.Workspace()
    cfg = _cfg(ws, gate)
    head = core.git("rev-parse", "HEAD", cwd=ws.root)
    files = core.git("ls-tree", "-r", head, "--", *cfg["scope"], cwd=ws.root).split("\n")
    hashes = {f.split("\t")[1]: f.split()[2] for f in files if f}
    import importlib.metadata as md
    versions = {"python": platform.python_version(), "git": core.git("--version", cwd=ws.root)}
    for pkg in ("behave", "mcp"):
        try:
            versions[pkg] = md.version(pkg)
        except md.PackageNotFoundError:
            versions[pkg] = "not installed"
    evidence = test_evidence(ws)
    rep = gatelib.evaluate(gate, ws)
    return {"gate": gate, "head": head, "scope": cfg["scope"],
            "scope_content_hashes": dict(sorted(hashes.items())),
            "scope_fingerprint": approvals.fingerprint(ws, head, tuple(cfg["scope"])),
            "gate_open": rep["open"], "gate_problems": rep["problems"],
            "approvals": approval_records(gate, ws), "waivers": query(gate, "waivers", ws),
            "changes": change_records(gate, ws), "spec_results": evidence["run"],
            "requirement_test_results": evidence["requirements"], "trace_report": rep["trace"],
            "ai_unreviewed": rep["ai_unreviewed"], "tool_versions": versions}


def main(argv):
    pos = [a for a in argv if not a.startswith("--")]
    if len(pos) < 2:
        print(__doc__)
        return 2
    gate, subject = pos[0], pos[1].replace("_", "-")
    try:
        result = bundle(gate) if subject == "bundle" else query(gate, subject)
    except core.Rejected as e:
        print(e, file=sys.stderr)
        return 1
    text = json.dumps(result, indent=2, sort_keys=True)
    if "--out" in argv:
        Path(argv[argv.index("--out") + 1]).write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0 if subject != "integrity" or result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
