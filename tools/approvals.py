"""Gate approval from per-stakeholder SSH-signed tags (SR-041, DR-003).

Each stakeholder role signs `approval/<gate>/<role>.<n>` (n = revision; an unversioned tag counts as revision 0)
with a key whose public half is in approvals/keys/<principal>.pub.
approvals/gates.json lists the gate scopes and required roles; approvals/roles.json maps principals to roles.
A gate is open when every required role has a valid tag signed by a principal holding that role, all tags cover the
same scope content on the same commit (a gate revision), and the working tree has not drifted from it. There is no separate "gate open" tag: the state
is derived. Tags are created by humans (tools/approve.py); agents can only read status.
"""
import hashlib
import json
import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

import specflow_core as core


@dataclass
class Verification:
    ok: bool
    signer: str = ""
    reason: str = ""


def _json(ws, name):
    f = ws.root / "approvals" / name
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}


def gates(ws):
    return _json(ws, "gates.json").get("gates", {})


def _signers(ws):
    lines = []
    for k in sorted((ws.root / "approvals/keys").glob("*.pub")):
        parts = k.read_text(encoding="utf-8").split()
        if len(parts) >= 2:
            lines.append(f'{k.stem} namespaces="git" {parts[0]} {parts[1]}')
    return lines


def verify_tag(name, ws=None):
    ws = ws or core.Workspace()
    if not core.git("tag", "--list", name, cwd=ws.root):
        return Verification(False, reason="tag missing")
    signers = _signers(ws)
    if not signers:
        return Verification(False, reason="no approver keys in approvals/keys")
    with tempfile.TemporaryDirectory() as tmp:
        f = Path(tmp) / "allowed_signers"
        f.write_text("\n".join(signers) + "\n", encoding="utf-8")
        r = subprocess.run(["git", "-c", "gpg.format=ssh", "-c", f"gpg.ssh.allowedSignersFile={f}", "verify-tag", name],
                           cwd=ws.root, capture_output=True, text=True)
    if r.returncode:
        return Verification(False, reason="signature invalid or signer not authorised")
    m = re.search(r'Good "git" signature for (\S+)', r.stdout + r.stderr)
    return Verification(True, signer=m.group(1) if m else "")


def role_tags(ws, gate, role):
    """All approval tags of a role for a gate as (revision, name), oldest first."""
    found = []
    for name in core.git("tag", "--list", f"approval/{gate}/{role}*", cwd=ws.root).split():
        m = re.fullmatch(re.escape(f"approval/{gate}/{role}") + r"(?:\.(\d+))?", name)
        if m:
            found.append((int(m.group(1) or 0), name))
    return sorted(found)


def current_tag(ws, gate, role):
    """Newest revision with a valid signature from a holder of the role; older revisions are superseded."""
    roles_of = _json(ws, "roles.json")
    last = None
    for rev, name in reversed(role_tags(ws, gate, role)):
        v = verify_tag(name, ws)
        if v.ok and role not in roles_of.get(v.signer, []):
            v = Verification(False, reason=f"signer {v.signer} does not hold role {role}")
        if v.ok:
            return name, rev, v
        last = last or (name, rev, v)
    return last or (f"approval/{gate}/{role}.1", 0, Verification(False, reason="tag missing"))


def _scope(ws, gate):
    return tuple(gates(ws).get(gate, {}).get("scope", ()))


def fingerprint(ws, commit, scope):
    """Hash of the scope content at a commit (paths and blob IDs)."""
    listing = core.git("ls-tree", "-r", commit, "--", *scope, cwd=ws.root)
    return hashlib.sha256(listing.encode()).hexdigest()


def drift(gate, ws=None, commit="HEAD"):
    """Scope files that differ between `commit` and the working tree (tracked changes or untracked files)."""
    ws = ws or core.Workspace()
    scope = _scope(ws, gate)
    if not scope:
        return []
    changed = core.git("diff", "--name-only", commit, "--", *scope, cwd=ws.root).split("\n")
    untracked = core.git("ls-files", "--others", "--exclude-standard", "--", *scope, cwd=ws.root).split("\n")
    return sorted({c for c in changed + untracked if c})


def _revision(ws, roles):
    """Gate revision = the commit being approved. Returns the newest approved commit, the roles that approved it,
    the roles still missing on it, and all commits that hold current approvals; None without valid approvals."""
    by_commit = {}
    for role, e in roles.items():
        if e["valid"]:
            by_commit.setdefault(e["commit"], []).append(role)
    if not by_commit:
        return None
    commits = list(by_commit)
    newest = next((c for c in commits if all(o == c or _is_ancestor(ws, o, c) for o in commits)), None)
    if newest is None:
        newest = max(commits, key=lambda c: int(core.git("show", "-s", "--format=%ct", c, cwd=ws.root)))
    return {"commit": newest, "approved": sorted(by_commit[newest]),
            "missing": [r for r in roles if r not in by_commit[newest]],
            "commits": {c: sorted(rs) for c, rs in by_commit.items()}}


def _is_ancestor(ws, older, newer):
    return subprocess.run(["git", "merge-base", "--is-ancestor", older, newer], cwd=ws.root, check=False).returncode == 0


def gate_status(gate, ws=None):
    ws = ws or core.Workspace()
    cfg = _json(ws, "gates.json")
    g = cfg.get("gates", {}).get(gate)
    if g is None:
        return {"gate": gate, "open": False, "problems": ["gate not configured"], "roles": {}, "drift": []}
    scope = tuple(g["scope"])
    roles, prints, signers = {}, set(), set()
    for role in g["roles"]:
        tag, rev, v = current_tag(ws, gate, role)
        entry = {"tag": tag, "revision": rev, "valid": v.ok, "signer": v.signer, "reason": v.reason}
        if entry["valid"]:
            commit = core.git("rev-parse", f"{tag}^{{commit}}", cwd=ws.root)
            fp = fingerprint(ws, commit, scope)
            entry["scope_fingerprint"] = fp
            entry["commit"] = commit
            prints.add(fp)
            signers.add(v.signer)
            entry["stale"] = bool(drift(gate, ws, commit))
        roles[role] = entry
    missing = [r for r, e in roles.items() if not e["valid"]]
    revision = _revision(ws, roles)
    stale = [r for r, e in roles.items() if e.get("stale")]
    single = len(signers) == 1 and not missing
    problems = []
    if missing:
        problems.append(f"missing or invalid approvals: {', '.join(missing)}")
    if len(prints) > 1:
        problems.append("approvals cover different scope content")
    elif revision and len(revision["commits"]) > 1:
        problems.append(f"approvals are on different commits; the newest revision {revision['commit'][:12]} "
                        f"still needs: {', '.join(revision['missing'])}")
    if stale:
        problems.append(f"scope changed since approval: {', '.join(stale)}")
    if single and not cfg.get("allow_single_person", False):
        problems.append("separation of duties: one person signed all roles")
    return {"gate": gate, "open": not problems, "problems": problems, "single_person": single,
            "revision": revision, "roles": roles, "drift": drift(gate, ws) if not missing else []}


def status(ws=None):
    ws = ws or core.Workspace()
    return {g: gate_status(g, ws) for g in gates(ws)}


def protected_files(ws):
    files = set()
    for gate, g in gates(ws).items():
        for tag in core.git("tag", "--list", f"approval/{gate}/*", cwd=ws.root).split():
            names = core.git("ls-tree", "-r", "--name-only", tag, "--", *g["scope"], cwd=ws.root).split("\n")
            files.update(n for n in names if n)
    return files


def create_approval(gate, role, message, ws=None, commit=None):
    """Human action: sign the next revision approval/<gate>/<role>.<n> with the operator's SSH key (git config user.signingkey).

    The tag is placed on `commit` (default HEAD). An earlier commit is accepted so approvers can join a gate revision (a stable baseline)
    although the repository has moved on; the gate then stays closed at HEAD while the scope differs from it."""
    ws = ws or core.Workspace()
    g = gates(ws).get(gate)
    if g is None or role not in g["roles"]:
        raise core.Rejected(f"role {role} is not required for gate {gate}; valid: {', '.join(g['roles']) if g else '(gate unknown)'}")
    if drift(gate, ws):
        raise core.Rejected("scope has uncommitted changes; commit them first so the approval covers what is signed")
    target = "HEAD"
    if commit:
        try:
            target = core.git("rev-parse", "--verify", f"{commit}^{{commit}}", cwd=ws.root)
        except RuntimeError:
            raise core.Rejected(f"unknown commit: {commit}")
        if not _is_ancestor(ws, target, "HEAD"):
            raise core.Rejected(f"commit {commit} is not part of the current history")
    existing = role_tags(ws, gate, role)
    name = f"approval/{gate}/{role}.{(existing[-1][0] if existing else 0) + 1}"
    core.git("-c", "gpg.format=ssh", "tag", "-s", name, target, "-m", message, cwd=ws.root)
    v = verify_tag(name, ws)
    if v.ok and role not in _json(ws, "roles.json").get(v.signer, []):
        v = Verification(False, reason=f"signer {v.signer} does not hold role {role}")
    if not v.ok:
        core.git("tag", "-d", name, cwd=ws.root)
        raise core.Rejected(f"tag deleted: {v.reason}")
    return v
