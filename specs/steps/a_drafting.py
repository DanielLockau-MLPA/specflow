"""Steps of 03_drafting.feature (shared draft-request and refusal steps are in a_workflow_qa.py)."""
import fnmatch
import json
import os
import re

from behave import given, then, when
from behave.parser import parse_feature

import a_mcp
import specflow_core as core

BASELINE_GATE = {"requirement": "G1", "model": "G2"}
PROPOSAL = "proposal/model-draft"


@given("no approved {level} baseline exists")
def no_baseline(context, level):
    assert not core.baseline_exists(BASELINE_GATE[level], context.world.ws)


@given("an approved {level} baseline")
def approved_baseline(context, level):
    context.world.approve_all(BASELINE_GATE[level])
    assert core.baseline_exists(BASELINE_GATE[level], context.world.ws)


def propose(context, path, content, branch):
    context.head_before = context.world.git("rev-parse", "main").stdout
    context.refused, context.reply = a_mcp.call(
        "model", "propose_edit", {"path": path, "content": content, "branch": branch, "message": "agent proposal"})
    context.branch, context.path = branch, path


@when("the agent proposes a model edit")
def propose_model_edit(context):
    propose(context, "model/50_draft.sysml", "package Draft {\n}\n", PROPOSAL)
    assert not context.refused, context.reply


@then('the change lands on a branch matching "{pattern}"')
def on_proposal_branch(context, pattern):
    branches = context.world.git("branch", "--list", "--format=%(refname:short)").stdout.split()
    assert context.branch in branches and fnmatch.fnmatch(context.branch, pattern), branches
    assert context.world.git("rev-parse", "main").stdout == context.head_before
    assert not (context.world.root / context.path).exists()
    assert context.world.git("show", f"{context.branch}:{context.path}").stdout.startswith("package Draft")


@then('the proposed content has the status "{status}"')
def draft_status(context, status):
    assert json.loads(context.reply)["status"] == status
    assert f"Status: {status}" in context.world.git("log", "-1", "--format=%B", context.branch).stdout


@when('the agent drafts scenarios for the requirement "{requirement}"')
def draft_scenarios(context, requirement):
    error, context.draft = a_mcp.call("spec", "draft_scenarios", {"requirement_id": requirement})
    assert not error, context.draft
    context.scenarios = parse_feature("Feature: Draft\n\n" + context.draft).scenarios
    assert context.scenarios


@then('each drafted scenario carries the tag "{tag}"')
def drafted_tag(context, tag):
    assert all(tag in [f"@{t}" for t in sc.effective_tags] for sc in context.scenarios)


@then("no drafted scenario carries a tag naming a non-existing element")
def drafted_tags_exist(context):
    known = core.model_ids(context.world.ws)
    tags = {str(t) for sc in context.scenarios for t in sc.effective_tags}
    assert tags and all(t in known for t in tags), tags


@given("a specification containing a scenario without any ID tag")
def untagged_scenario(context):
    (context.world.root / "specs/features/untagged.feature").write_text(
        "Feature: Untagged\n\n  Scenario: No tag\n    Given nothing\n", encoding="utf-8")


@when("I run the spec check")
def spec_check(context):
    context.check = context.world.cli("trace", "--stage", "spec", "--json")
    context.violations = json.loads(context.check.stdout)["violations"]


@then("the check reports the scenario as invalid")
def scenario_invalid(context):
    assert context.check.returncode == 1
    hit = [v for v in context.violations if v["rule"] == "scenario-tagged"]
    assert [v["element"] for v in hit] == ["untagged.feature:3"], hit


@when('the agent writes a proposal to "{ref}"')
def write_to_ref(context, ref):
    propose(context, "model/50_draft.sysml", "package Draft {\n}\n", ref)


@then("the write is {outcome}")
def write_outcome(context, outcome):
    branches = context.world.git("branch", "--list", "--format=%(refname:short)").stdout.split()
    if outcome == "accepted":
        assert not context.refused, context.reply
        assert context.branch in branches
    else:
        assert outcome == "rejected" and context.refused, context.reply
        assert context.branch not in branches or context.branch == "main"
        assert context.world.git("rev-parse", "main").stdout == context.head_before
        assert not context.world.git("status", "--porcelain").stdout.strip()
        assert re.search(r"proposal/\*|approved baseline", context.reply), context.reply


@given('the operator unlocked the proposal branch "{branch}"')
def operator_unlock(context, branch):
    old = os.environ.get("SPECFLOW_UNLOCK_BRANCHES")
    os.environ["SPECFLOW_UNLOCK_BRANCHES"] = branch
    context.add_cleanup(lambda: os.environ.pop("SPECFLOW_UNLOCK_BRANCHES", None) if old is None
                        else os.environ.__setitem__("SPECFLOW_UNLOCK_BRANCHES", old))


@then('the commit on the proposal branch carries the trailer "{trailer}"')
def commit_trailer(context, trailer):
    message = context.world.git("log", "-1", "--format=%B", context.branch).stdout
    assert re.search(rf"^{re.escape(trailer)}: {re.escape(context.path)}$", message, re.M), message


@when("the agent proposes a change to a file of that baseline")
def change_baseline_file(context):
    path = "model/20_system_requirements.sysml"
    assert path in core.baseline_files(context.world.ws)
    propose(context, path, "changed\n", PROPOSAL)
