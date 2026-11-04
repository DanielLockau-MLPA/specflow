# SPDX-FileCopyrightText: (C) 2026 ML!PA Consulting GmbH
# SPDX-License-Identifier: MIT

"""Out-of-band human confirmation (DR-032) for clients that cannot answer MCP elicitation.

Server side: a state-changing tool call stores a pending request in .specflow/pending/ and waits. The human decides in a
separate terminal, outside the agent session, with their own SSH key; only a signature from a key in approvals/keys whose
principal holds a role in approvals/roles.json counts. The signed text binds the decision to the request ID and the exact
message, so a signature cannot be replayed for another request or message.

Human side:
  uv run python tools/confirm_oob.py list
  uv run python tools/confirm_oob.py approve <id> [--key ~/.ssh/id_ed25519]
  uv run python tools/confirm_oob.py deny <id> [--key ...]
Needs an interactive terminal and the signing key (git config user.signingkey if --key is omitted).
"""
import argparse
import asyncio
import contextlib
import hashlib
import json
import re
import secrets
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import specflow_core as core

NAMESPACE = "specflow-confirm"
POLL_SECONDS = 0.5


def pending_dir(ws):
    return ws.root / ".specflow" / "pending"


def payload(request_id, message, decision):
    digest = hashlib.sha256(message.encode("utf-8")).hexdigest()
    return f"{NAMESPACE}\nid={request_id}\nmessage-sha256={digest}\ndecision={decision}\n"


def _allowed_signers(ws):
    roles = json.loads((ws.root / "approvals/roles.json").read_text(encoding="utf-8")) \
        if (ws.root / "approvals/roles.json").exists() else {}
    lines = []
    for k in sorted((ws.root / "approvals/keys").glob("*.pub")):
        parts = k.read_text(encoding="utf-8").split()
        if len(parts) >= 2 and roles.get(k.stem):
            lines.append(f'{k.stem} namespaces="{NAMESPACE}" {parts[0]} {parts[1]}')
    return lines


def verify(ws, request_id, message, decision, signature):
    """Return the signer principal if `signature` is a valid signature of this request and decision, else None."""
    signers = _allowed_signers(ws)
    if not signers:
        return None
    with tempfile.TemporaryDirectory() as tmp:
        allowed, sig = Path(tmp) / "allowed_signers", Path(tmp) / "sig"
        allowed.write_text("\n".join(signers) + "\n", encoding="utf-8")
        sig.write_text(signature, encoding="utf-8")
        text = payload(request_id, message, decision)
        found = subprocess.run(["ssh-keygen", "-Y", "find-principals", "-s", str(sig), "-f", str(allowed)],
                               capture_output=True, text=True, check=False)
        for principal in found.stdout.split():
            ok = subprocess.run(["ssh-keygen", "-Y", "verify", "-f", str(allowed), "-I", principal, "-n", NAMESPACE,
                                 "-s", str(sig)], input=text, capture_output=True, text=True, check=False)
            if ok.returncode == 0:
                return principal
    return None


def create_request(ws, message, timeout):
    request_id = secrets.token_hex(8)
    d = pending_dir(ws)
    d.mkdir(parents=True, exist_ok=True)
    now = time.time()
    (d / f"{request_id}.json").write_text(json.dumps(
        {"id": request_id, "message": message, "created": now, "expires": now + timeout}), encoding="utf-8")
    return request_id


def _cleanup(ws, request_id):
    for f in pending_dir(ws).glob(f"{request_id}.*"):
        f.unlink(missing_ok=True)


async def confirm(ctx, message, timeout, ws=None):
    """Wait for a signed human decision; any outcome other than a valid signed approval aborts the call."""
    ws = ws or core.Workspace()
    request_id = create_request(ws, message, timeout)
    hint = f"confirmation {request_id} pending: run 'uv run python tools/confirm_oob.py approve {request_id}' in a separate terminal"
    with contextlib.suppress(Exception):  # a missing log channel must not block the wait
        if ctx is not None:
            await ctx.info(hint)
    deadline = time.monotonic() + timeout
    try:
        while time.monotonic() < deadline:
            for decision in ("deny", "approve"):
                f = pending_dir(ws) / f"{request_id}.{decision}.sig"
                if f.exists() and verify(ws, request_id, message, decision, f.read_text(encoding="utf-8")):
                    if decision == "deny":
                        raise core.Rejected("human declined; call aborted")
                    return
            await asyncio.sleep(POLL_SECONDS)
    finally:
        _cleanup(ws, request_id)
    raise core.Rejected(f"no signed human answer within the confirmation timeout ({hint}); call aborted")


# --- human CLI -----------------------------------------------------------------

def _load(ws, request_id):
    if not re.fullmatch(r"[0-9a-f]{16}", request_id):
        raise core.Rejected("invalid request id")
    f = pending_dir(ws) / f"{request_id}.json"
    if not f.exists():
        raise core.Rejected(f"no pending request {request_id}")
    req = json.loads(f.read_text(encoding="utf-8"))
    if req["expires"] < time.time():
        raise core.Rejected(f"request {request_id} expired")
    return req


def sign_decision(ws, request_id, decision, key):
    req = _load(ws, request_id)
    with tempfile.TemporaryDirectory() as tmp:
        data = Path(tmp) / "payload"
        data.write_text(payload(request_id, req["message"], decision), encoding="utf-8")
        r = subprocess.run(["ssh-keygen", "-Y", "sign", "-f", str(key), "-n", NAMESPACE, str(data)],
                           check=False)
        if r.returncode:
            raise core.Rejected("signing failed")
        sig = Path(f"{data}.sig").read_text(encoding="utf-8")
    (pending_dir(ws) / f"{request_id}.{decision}.sig").write_text(sig, encoding="utf-8")


def _default_key():
    r = subprocess.run(["git", "config", "user.signingkey"], capture_output=True, text=True, check=False)
    return Path(r.stdout.strip()).expanduser() if r.stdout.strip() else None


def main(argv=None):
    ap = argparse.ArgumentParser(description="Human decision on a pending agent request")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    for name in ("approve", "deny"):
        p = sub.add_parser(name)
        p.add_argument("id")
        p.add_argument("--key", type=Path, help="SSH private key (default: git config user.signingkey)")
    a = ap.parse_args(argv)
    ws = core.Workspace()
    try:
        if a.cmd == "list":
            for f in sorted(pending_dir(ws).glob("*.json")):
                req = json.loads(f.read_text(encoding="utf-8"))
                if req["expires"] >= time.time():
                    print(f"{req['id']}  {req['message']}")
            return 0
        if not sys.stdin.isatty():
            raise core.Rejected("run this command in an interactive terminal outside the agent session")
        req = _load(ws, a.id)
        print(f"Request {req['id']}:\n  {req['message']}")
        key = a.key or _default_key()
        if not key:
            raise core.Rejected("no signing key: pass --key or set git config user.signingkey")
        sign_decision(ws, a.id, a.cmd, key)
        print(f"{a.cmd} signed")
        return 0
    except core.Rejected as e:
        print(e, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
