import asyncio
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
from mcp import Client, types  # noqa: E402

import mcp_model  # noqa: E402
import specflow_core as core  # noqa: E402


def sh(cwd, *a):
    subprocess.run(a, cwd=cwd, check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path, monkeypatch):
    sh(tmp_path, "git", "init", "-q", "-b", "proposal/test")
    sh(tmp_path, "git", "config", "user.email", "t@example.com")
    sh(tmp_path, "git", "config", "user.name", "t")
    (tmp_path / "model").mkdir()
    (tmp_path / "model/a.sysml").write_text("x")
    (tmp_path / "inputs.txt").write_text("hello")
    sh(tmp_path, "git", "add", "-A")
    sh(tmp_path, "git", "commit", "-q", "-m", "init")
    monkeypatch.setattr(core, "ROOT", tmp_path.resolve())
    return tmp_path


def make_key(directory, name):
    key = directory / name
    sh(directory, "ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(key))
    return key


def sign_tag(repo, tag, key):
    sh(repo, "git", "-c", "gpg.format=ssh", "-c", f"user.signingkey={key}", "tag", "-s", tag, "-m", "approved")


@pytest.fixture
def approver(repo, tmp_path_factory):
    keys = tmp_path_factory.mktemp("keys")
    key = make_key(keys, "approver")
    (repo / "approvals/keys").mkdir(parents=True)
    (repo / "approvals/keys/approver.pub").write_text((keys / "approver.pub").read_text())
    return key


def call(name, args, answer="accept", approve=True):
    async def cb(ctx, params):
        return types.ElicitResult(action=answer, content={"approve": approve} if answer == "accept" else None)

    async def run():
        async with Client(mcp_model.mcp, elicitation_callback=cb, mode="legacy") as c:
            r = await c.call_tool(name, args)
            return r.is_error, "".join(x.text for x in r.content)
    return asyncio.run(run())


def test_path_guard(repo):
    for p in ("../etc/passwd", ".git/config", "/etc/passwd"):
        err, text = call("read_document", {"path": p})
        assert err and ("outside workspace" in text or "protected" in text), p
    err, text = call("read_document", {"path": "inputs.txt"})
    assert not err and "untrusted" in text.lower()


def test_symlink_escape_rejected(repo, tmp_path_factory):
    outside = tmp_path_factory.mktemp("out") / "s.txt"
    outside.write_text("secret")
    (repo / "link.txt").symlink_to(outside)
    err, _ = call("read_document", {"path": "link.txt"})
    assert err


def test_propose_edit_needs_confirmation_and_proposal_branch(repo):
    args = {"path": "model/b.sysml", "content": "y", "branch": "proposal/x", "message": "m"}
    assert call("propose_edit", args, answer="decline")[0]
    assert call("propose_edit", args, approve=False)[0]
    assert call("propose_edit", {**args, "branch": "main"})[0]
    err, text = call("propose_edit", args)
    assert not err, text
    log = subprocess.run(["git", "log", "-1", "--format=%B", "proposal/x"], cwd=repo, capture_output=True, text=True).stdout
    assert "AI-Authored-By:" in log and "Status: DRAFT" in log
    assert not (repo / "model/b.sysml").exists()


def test_propose_edit_refuses_baseline_files(repo, approver):
    sign_tag(repo, "baseline/G2", approver)
    err, text = call("propose_edit", {"path": "model/a.sysml", "content": "z", "branch": "proposal/y", "message": "m"})
    assert err and "baseline" in text


def test_decision_log_validates_ids_and_appends(repo):
    base = {"stage": "model", "kind": "qa", "participants": ["h"], "question": "q", "decision": "d", "rationale": "r"}
    assert call("record_decision", {**base, "affected": ["SR-999"]})[0]
    assert not call("record_decision", {**base, "affected": ["SR-001"]})[0]
    assert not call("record_decision", {**base, "affected": ["SR-002"]})[0]
    text = (repo / "decisions/model.md").read_text()
    assert "DL-001" in text and "DL-002" in text


def test_model_draft_requires_baseline_and_qa(repo, approver):
    err, text = call("request_model_draft", {})
    assert err and "baseline" in text
    sign_tag(repo, "baseline/G1", approver)
    err, text = call("request_model_draft", {})
    assert err and "Q&A" in text


def test_prompts_forbid_approval_and_require_logging():
    async def run():
        async with Client(mcp_model.mcp, mode="legacy") as c:
            names = {p.name for p in (await c.list_prompts()).prompts}
            text = (await c.get_prompt("model_qa")).messages[0].content.text
            return names, text
    names, text = asyncio.run(run())
    assert {"model_qa", "spec_qa", "review"} <= names
    assert "Ask questions first" in text and "record_decision" in text and "Never claim" in text


def test_unsigned_or_foreign_signed_baseline_is_not_accepted(repo, approver, tmp_path_factory):
    import approvals
    sh(repo, "git", "tag", "-a", "baseline/G1", "-m", "unsigned")
    assert not approvals.verify_tag("baseline/G1").ok
    stranger = make_key(tmp_path_factory.mktemp("s"), "stranger")
    sign_tag(repo, "baseline/G2", stranger)
    assert not approvals.verify_tag("baseline/G2").ok
    sign_tag(repo, "baseline/G3", approver)
    v = approvals.verify_tag("baseline/G3")
    assert v.ok and v.signer == "approver"


def test_drift_detected_in_scope_only(repo, approver):
    import approvals
    sign_tag(repo, "baseline/G2", approver)
    (repo / "inputs.txt").write_text("changed")
    assert approvals.drift("baseline/G2") == []
    (repo / "model/a.sysml").write_text("changed")
    (repo / "model/new.sysml").write_text("new")
    assert approvals.drift("baseline/G2") == ["model/a.sysml", "model/new.sysml"]


def test_approver_keys_are_protected_from_agent(repo):
    err, text = call("read_document", {"path": "approvals/keys/x.pub"})
    assert err and "protected" in text
    err, text = call("propose_edit", {"path": "approvals/keys/evil.pub", "content": "k", "branch": "proposal/k", "message": "m"})
    assert err and "protected" in text


def test_baseline_outside_gate_scope_stays_editable(repo, approver):
    sign_tag(repo, "baseline/G2", approver)
    err, text = call("propose_edit", {"path": "inputs.txt", "content": "n", "branch": "proposal/z", "message": "m"})
    assert not err, text
