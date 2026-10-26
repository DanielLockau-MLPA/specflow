"""Baseline approval: SSH-signed git tags verified against the public keys in approvals/keys (SR-041, DR-003).

Tags are created by humans with `approve.py baseline`; agents have no path to this module's write functions
(MCP tools only call verify_tag/status). The directory approvals/ is protected from the file guard.
"""
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


def drift(name, ws=None):
    """Files in the gate scope that differ between the tag and the working tree (tracked or untracked)."""
    ws = ws or core.Workspace()
    scope = core.SCOPES.get(name, ("",))
    changed = core.git("diff", "--name-only", name, "--", *scope, cwd=ws.root).split("\n")
    untracked = core.git("ls-files", "--others", "--exclude-standard", "--", *scope, cwd=ws.root).split("\n")
    return sorted({c for c in changed + untracked if c})


def status(ws=None):
    ws = ws or core.Workspace()
    out = {}
    for name in ("baseline/G1", "baseline/G2", "baseline/G3"):
        v = verify_tag(name, ws)
        out[name] = {"verified": v.ok, "signer": v.signer, "reason": v.reason, "drift": drift(name, ws) if v.ok else []}
    return out


def create_baseline(gate, message, ws=None):
    """Human action: create the signed tag with the operator's own SSH key (git config user.signingkey)."""
    ws = ws or core.Workspace()
    name = f"baseline/{gate}"
    if name not in core.SCOPES:
        raise core.Rejected(f"unknown gate: {gate}")
    core.git("-c", "gpg.format=ssh", "tag", "-s", name, "-m", message, cwd=ws.root)
    v = verify_tag(name, ws)
    if not v.ok:
        core.git("tag", "-d", name, cwd=ws.root)
        raise core.Rejected(f"tag deleted: not verifiable against approvals/keys ({v.reason})")
    return v
