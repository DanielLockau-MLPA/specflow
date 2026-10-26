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


def test_propose_edit_refuses_baseline_files(repo):
    sh(repo, "git", "tag", "baseline/G2")
    err, text = call("propose_edit", {"path": "model/a.sysml", "content": "z", "branch": "proposal/y", "message": "m"})
    assert err and "baseline" in text


def test_decision_log_validates_ids_and_appends(repo):
    base = {"stage": "model", "kind": "qa", "participants": ["h"], "question": "q", "decision": "d", "rationale": "r"}
    assert call("record_decision", {**base, "affected": ["SR-999"]})[0]
    assert not call("record_decision", {**base, "affected": ["SR-001"]})[0]
    assert not call("record_decision", {**base, "affected": ["SR-002"]})[0]
    text = (repo / "decisions/model.md").read_text()
    assert "DL-001" in text and "DL-002" in text


def test_model_draft_requires_baseline_and_qa(repo):
    err, text = call("request_model_draft", {})
    assert err and "baseline" in text
    sh(repo, "git", "tag", "baseline/G1")
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
