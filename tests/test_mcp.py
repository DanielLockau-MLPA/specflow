# SPDX-FileCopyrightText: (C) 2026 ML!PA Consulting GmbH
# SPDX-License-Identifier: MIT

import asyncio
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
from mcp import Client, types

import mcp_model
import specflow_core as core


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
    roles = ["reviewer", "owner"]
    (repo / "approvals/gates.json").write_text(json.dumps({"allow_single_person": True, "gates": {
        "G1": {"scope": ["inputs.txt"], "roles": roles}, "G2": {"scope": ["model/"], "roles": roles},
        "G3": {"scope": ["specs/"], "roles": roles}}}))
    (repo / "approvals/roles.json").write_text(json.dumps({"approver": roles}))
    return key


def approve_gate(repo, gate, key, roles=("reviewer", "owner")):
    for r in roles:
        sign_tag(repo, f"approval/{gate}/{r}", key)


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
    log = subprocess.run(["git", "log", "-1", "--format=%B", "proposal/x"], cwd=repo, capture_output=True, text=True, check=True).stdout
    assert "AI-Authored-By:" in log and "Status: DRAFT" in log
    assert not (repo / "model/b.sysml").exists()


def test_propose_edit_refuses_baseline_files(repo, approver):
    approve_gate(repo, "G2", approver)
    err, text = call("propose_edit", {"path": "model/a.sysml", "content": "z", "branch": "proposal/y", "message": "m"})
    assert err and "baseline" in text


def test_unlocked_branch_allows_baseline_files_with_trailer(repo, approver, monkeypatch):
    approve_gate(repo, "G2", approver)
    args = {"path": "model/a.sysml", "content": "z", "message": "m"}
    monkeypatch.setenv("SPECFLOW_UNLOCK_BRANCHES", "proposal/open*")
    assert call("propose_edit", {**args, "branch": "proposal/other"})[0]
    assert call("propose_edit", {**args, "branch": "main"})[0]
    err, text = call("propose_edit", {**args, "branch": "proposal/open-1"})
    assert not err, text
    log = subprocess.run(["git", "log", "-1", "--format=%B", "proposal/open-1"], cwd=repo, capture_output=True, text=True, check=True).stdout
    assert "Unlocked-Baseline: model/a.sysml" in log
    err, _ = call("propose_edit", {"path": "approvals/gates.json", "content": "{}", "branch": "proposal/open-1", "message": "m"})
    assert err


def test_decision_log_validates_ids_and_appends(repo):
    shutil.copytree(core.CODE_ROOT / "model", repo / "model", dirs_exist_ok=True)
    base = {"stage": "model", "kind": "qa", "participants": ["h"], "question": "q", "decision": "d", "rationale": "r"}
    assert call("record_decision", {**base, "affected": ["SR-999"]})[0]
    assert not call("record_decision", {**base, "affected": ["SR-001"]})[0]
    assert not call("record_decision", {**base, "affected": ["SR-002"]})[0]
    text = (repo / "decisions/model.md").read_text()
    assert "DL-001" in text and "DL-002" in text


def test_model_draft_requires_baseline_and_qa(repo, approver):
    err, text = call("request_model_draft", {})
    assert err and "gate G1 is not open" in text
    approve_gate(repo, "G1", approver)
    err, text = call("request_model_draft", {})
    assert err and "Q&A" in text


def test_prompts_forbid_approval_and_require_logging():
    async def run():
        async with Client(mcp_model.mcp, mode="legacy") as c:
            names = {p.name for p in (await c.list_prompts()).prompts}
            text = (await c.get_prompt("model-qa")).messages[0].content.text
            return names, text
    names, text = asyncio.run(run())
    assert {"model-qa", "spec-qa", "review"} <= names
    assert "Ask questions first" in text and "record_decision" in text and "Never claim" in text


def test_gate_needs_all_roles_signed_by_authorised_keys(repo, approver, tmp_path_factory):
    import approvals
    sign_tag(repo, "approval/G2/reviewer", approver)
    st = approvals.gate_status("G2")
    assert not st["open"] and "owner" in st["problems"][0]
    sh(repo, "git", "tag", "-a", "approval/G2/owner", "-m", "unsigned")
    assert not approvals.gate_status("G2")["open"]
    sh(repo, "git", "tag", "-d", "approval/G2/owner")
    stranger = make_key(tmp_path_factory.mktemp("s"), "stranger")
    sign_tag(repo, "approval/G2/owner", stranger)
    assert not approvals.gate_status("G2")["open"]
    sh(repo, "git", "tag", "-d", "approval/G2/owner")
    sign_tag(repo, "approval/G2/owner", approver)
    st = approvals.gate_status("G2")
    assert st["open"] and st["single_person"]


def test_single_person_requires_explicit_allowance(repo, approver):
    import approvals
    approve_gate(repo, "G2", approver)
    assert approvals.gate_status("G2")["open"]
    cfg = json.loads((repo / "approvals/gates.json").read_text())
    cfg["allow_single_person"] = False
    (repo / "approvals/gates.json").write_text(json.dumps(cfg))
    st = approvals.gate_status("G2")
    assert not st["open"] and "separation of duties" in st["problems"][0]


def test_signer_must_hold_the_role(repo, approver):
    import approvals
    (repo / "approvals/roles.json").write_text(json.dumps({"approver": ["reviewer"]}))
    approve_gate(repo, "G2", approver)
    st = approvals.gate_status("G2")
    assert not st["open"] and "does not hold role owner" in st["roles"]["owner"]["reason"]


def test_changed_scope_invalidates_approvals(repo, approver):
    import approvals
    approve_gate(repo, "G2", approver)
    (repo / "inputs.txt").write_text("changed")
    assert approvals.gate_status("G2")["open"]
    (repo / "model/a.sysml").write_text("changed")
    sh(repo, "git", "commit", "-qam", "change")
    st = approvals.gate_status("G2")
    assert not st["open"] and "scope changed" in " ".join(st["problems"])


def test_roles_must_agree_on_content(repo, approver):
    import approvals
    sign_tag(repo, "approval/G2/reviewer", approver)
    (repo / "model/a.sysml").write_text("changed")
    sh(repo, "git", "commit", "-qam", "change")
    sign_tag(repo, "approval/G2/owner", approver)
    st = approvals.gate_status("G2")
    assert not st["open"] and "different scope content" in " ".join(st["problems"])


def test_create_approval_refuses_uncommitted_scope(repo, approver):
    import approvals
    (repo / "model/a.sysml").write_text("changed")
    with pytest.raises(core.Rejected):
        approvals.create_approval("G2", "reviewer", "m")


def test_approver_keys_are_protected_from_agent(repo):
    err, text = call("read_document", {"path": "approvals/keys/x.pub"})
    assert err and "protected" in text
    err, text = call("propose_edit", {"path": "approvals/keys/evil.pub", "content": "k", "branch": "proposal/k", "message": "m"})
    assert err and "protected" in text


def test_baseline_outside_gate_scope_stays_editable(repo, approver):
    approve_gate(repo, "G2", approver)
    err, text = call("propose_edit", {"path": "inputs.txt", "content": "n", "branch": "proposal/z", "message": "m"})
    assert not err, text


def test_decision_log_is_append_only_through_proposals(repo):
    shutil.copytree(core.CODE_ROOT / "model", repo / "model", dirs_exist_ok=True)
    base = {"stage": "model", "kind": "qa", "participants": ["h"], "question": "q", "decision": "d", "rationale": "r",
            "affected": ["SR-001"]}
    assert not call("record_decision", base)[0]
    sh(repo, "git", "add", "-A")
    sh(repo, "git", "commit", "-qm", "log")
    old = (repo / "decisions/model.md").read_text()
    edit = {"path": "decisions/model.md", "branch": "proposal/log", "message": "m"}
    assert call("propose_edit", {**edit, "content": old.replace("DL-001", "DL-009")})[0]
    assert call("propose_edit", {**edit, "content": ""})[0]
    assert not call("propose_edit", {**edit, "content": old + "\n## DL-002\n"})[0]


def test_new_revision_supersedes_old_and_keeps_history(repo, approver):
    import approvals
    approve_gate(repo, "G2", approver)
    (repo / "model/a.sysml").write_text("changed")
    sh(repo, "git", "commit", "-qam", "change")
    assert not approvals.gate_status("G2")["open"]
    sh(repo, "git", "config", "user.signingkey", str(approver))
    for role in ("reviewer", "owner"):
        approvals.create_approval("G2", role, "re-approve")
    st = approvals.gate_status("G2")
    assert st["open"] and st["roles"]["owner"]["revision"] == 1
    assert [r for r, _ in approvals.role_tags(core.Workspace(), "G2", "owner")] == [0, 1]
