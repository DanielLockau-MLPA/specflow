# SPDX-FileCopyrightText: (C) 2026 ML!PA Consulting GmbH
# SPDX-License-Identifier: MIT

import asyncio
import functools
import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import confirm_oob
import specflow_core as core


def aio(fn):
    @functools.wraps(fn)
    def run(*a, **k):
        return asyncio.run(fn(*a, **k))
    return run


def keygen(directory, name):
    key = directory / name
    subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(key)], check=True, capture_output=True)
    return key


@pytest.fixture
def ws(tmp_path, monkeypatch):
    root = tmp_path / "ws"
    (root / "approvals/keys").mkdir(parents=True)
    key = keygen(tmp_path, "human")
    (root / "approvals/keys/human.pub").write_text((tmp_path / "human.pub").read_text())
    (root / "approvals/roles.json").write_text(json.dumps({"human": ["reviewer"]}))
    monkeypatch.setattr(core, "ROOT", root.resolve())
    w = core.Workspace()
    w.key = key
    w.stranger = keygen(tmp_path, "stranger")
    return w


class NoElicit:
    async def elicit(self, *a, **k):
        raise RuntimeError("client cannot elicit")


async def pending_id(ws):
    for _ in range(50):
        files = list(confirm_oob.pending_dir(ws).glob("*.json"))
        if files:
            return files[0].stem
        await asyncio.sleep(0.05)
    raise AssertionError("no pending request")


async def decide(ws, decision, key, message="Commit x"):
    task = asyncio.create_task(confirm_oob.confirm(None, message, 2, ws))
    request_id = await pending_id(ws)
    confirm_oob.sign_decision(ws, request_id, decision, key)
    return task


@aio
async def test_signed_approval_lets_the_call_proceed(ws):
    await (await decide(ws, "approve", ws.key))
    assert not list(confirm_oob.pending_dir(ws).glob("*"))


@aio
async def test_signed_denial_aborts(ws):
    with pytest.raises(core.Rejected, match="declined"):
        await (await decide(ws, "deny", ws.key))


@aio
async def test_signature_of_a_key_without_role_is_ignored(ws):
    with pytest.raises(core.Rejected, match="no signed human answer"):
        await (await decide(ws, "approve", ws.stranger))


@aio
async def test_signature_is_bound_to_request_and_message(ws):
    task = asyncio.create_task(confirm_oob.confirm(None, "Commit x", 1, ws))
    request_id = await pending_id(ws)
    confirm_oob.sign_decision(ws, request_id, "approve", ws.key)
    sig = (confirm_oob.pending_dir(ws) / f"{request_id}.approve.sig").read_text()
    assert confirm_oob.verify(ws, request_id, "Commit x", "approve", sig) == "human"
    assert confirm_oob.verify(ws, request_id, "Commit y", "approve", sig) is None
    assert confirm_oob.verify(ws, "0" * 16, "Commit x", "approve", sig) is None
    assert confirm_oob.verify(ws, request_id, "Commit x", "deny", sig) is None
    await task


@aio
async def test_auto_mode_falls_back_when_the_client_cannot_elicit(ws, monkeypatch):
    monkeypatch.setenv("SPECFLOW_CONFIRM_MODE", "auto")
    monkeypatch.setenv("SPECFLOW_CONFIRM_TIMEOUT", "2")
    task = asyncio.create_task(core.confirm(NoElicit(), "Commit x"))
    request_id = await pending_id(ws)
    confirm_oob.sign_decision(ws, request_id, "approve", ws.key)
    await task


@aio
async def test_default_mode_stays_closed_without_a_channel(ws):
    with pytest.raises(core.Rejected, match="no confirmation channel"):
        await core.confirm(NoElicit(), "Commit x")
    assert not list(confirm_oob.pending_dir(ws).glob("*"))


@aio
async def test_invalid_mode_is_refused(ws, monkeypatch):
    monkeypatch.setenv("SPECFLOW_CONFIRM_MODE", "tty")
    with pytest.raises(core.Rejected, match="invalid SPECFLOW_CONFIRM_MODE"):
        await core.confirm(NoElicit(), "Commit x")
