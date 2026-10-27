"""Steps of 07_change_control.feature."""
import json
import re

from behave import given, then, when

import approvals
import audit
import gate as gatelib
import impact
import tracecheck
from c_approvals_gates import record_run

ID = re.compile(r"[A-Z]{1,3}-\d+")


@when('I analyse the impact of a change to "{element}"')
def analyse_impact(context, element):
    context.element = element
    context.impact = impact.analyse(element, context.world.ws)


@then('the impact lists the upstream elements "{upstream}"')
def impact_upstream(context, upstream):
    expected = set(ID.findall(upstream))
    assert expected <= set(context.impact["upstream"]), f"expected {sorted(expected)}, model says {context.impact['upstream']}"


@then('the impact lists the downstream elements and scenarios "{downstream}"')
def impact_downstream(context, downstream):
    expected = set(ID.findall(downstream))
    assert expected <= set(context.impact["downstream"]), f"expected {sorted(expected)}, model says {context.impact['downstream']}"
    if "scenarios" in downstream:
        tagged = {f"{s['file']}:{s['line']} {s['name']}" for s in tracecheck.load_scenarios()
                  if {context.element, *context.impact["downstream"]} & set(s["tags"])}
        assert tagged and tagged <= set(context.impact["scenarios"])


@then('gate "{gate}" requires re-approval before any gate that relies on it opens')
def requires_reapproval(context, gate):
    assert not approvals.gate_status(gate, context.world.ws)["open"]
    rep = impact.analyse(context.changed_element, context.world.ws)
    assert gate in rep["gates_needing_reapproval"]
    context.impact = rep
    assert not gatelib.evaluate("G4", context.world.ws)["open"]


@then("the impact names the affected elements and scenarios")
def impact_names(context):
    assert context.impact["downstream"] and context.impact["scenarios"]


def edit_on_branch(world, element, author, trailers):
    world.git("checkout", "-q", "-b", "proposal")
    world.edit_element(element, f"{element} revised by {author}")
    world.commit(f"change {element}", author=author, trailers=trailers)
    sha = world.git("rev-parse", "HEAD").stdout.strip()
    world.git("checkout", "-q", "main")
    world.git("merge", "-q", "--ff-only", "proposal")
    return sha


@when('"{author}" changes "{element}" on a proposal branch with the reason "{reason}" and "{approver}" approves it')
def change_with_record(context, author, element, reason, approver):
    context.change = edit_on_branch(context.world, element, author,
                                    [f"Change-Reason: {reason}", f"Approved-By: {approver}"])
    context.expected = (author, reason, approver)


@when('"{author}" changes "{element}" without a reason')
def change_without_reason(context, author, element):
    context.change = edit_on_branch(context.world, element, author, [])


@then("the change record names who, when, why and the approver")
def record_complete(context):
    author, reason, approver = context.expected
    rec = next(r for r in audit.change_records("G2", context.world.ws) if r["commit"] == context.change)
    assert (rec["who"], rec["why"], rec["approver"]) == (author, reason, approver), rec
    assert re.match(r"\d{4}-\d\d-\d\dT", rec["when"]) and rec["complete"], rec


@then("the change record is retained in the history")
def record_retained(context):
    context.world.git("merge-base", "--is-ancestor", context.change, "HEAD")
    assert any(r["commit"] == context.change for r in audit.change_records("G2", context.world.ws))


@then("the change is reported as an incomplete change record")
def record_incomplete(context):
    rec = next(r for r in audit.change_records("G2", context.world.ws) if r["commit"] == context.change)
    assert not rec["complete"] and "no reason" in rec["problems"] and "no approver" in rec["problems"], rec


@given('gate "{gate}" is open after a passing specification run')
def open_after_run(context, gate):
    context.world.approve_all(gate)
    record_run(context.world)
    rep = gatelib.evaluate(gate, context.world.ws)
    assert rep["open"], rep["problems"]


@when('I inspect the evidence bundle of "{gate}"')
def inspect_bundle(context, gate):
    context.bundle = audit.bundle(gate, context.world.ws)


@then("the bundle contains the scope content hashes, the approvals, the waivers, the spec results, the trace report "
      "and the tool versions")
def bundle_contents(context):
    b = context.bundle
    assert b["scope_content_hashes"] and all(len(h) == 40 for h in b["scope_content_hashes"].values())
    assert b["scope_fingerprint"]
    assert len(b["approvals"]) == len(context.world.roles_of("G3")) and all(a["valid"] for a in b["approvals"])
    assert set(b["waivers"]) == {"valid", "invalid"}
    assert b["spec_results"]["summary"].get("passed") and b["spec_results"]["current"]
    assert b["trace_report"]["stages"] == ["needs", "model", "spec"] and not b["trace_report"]["violations"]
    assert all(b["tool_versions"][k] for k in ("python", "git", "behave"))


@then("each requirement is linked to its test results")
def requirements_linked(context):
    results = context.bundle["requirement_test_results"]
    info, _links, _alloc = tracecheck.load_model()
    requirements = sorted(i for i in info if i.startswith("SR-"))
    missing = [r for r in requirements if not results.get(r)]
    assert requirements and not missing, f"requirements without test results: {missing}"
    assert all(x["status"] == "passed" for r in requirements for x in results[r])


@given('gate "{gate}" with approvals, waivers, changes and test evidence')
def gate_with_evidence(context, gate):
    world = context.world
    world.approve_all(gate)
    feature = world.root / "specs/features/01_workflow_qa.feature"
    feature.write_text(feature.read_text(encoding="utf-8") + "\n# reviewed wording\n", encoding="utf-8")
    world.commit("clarify wording", author="alice", trailers=["Change-Reason: clarify", "Approved-By: bob"])
    world.approve_all(gate)
    world.sign_waiver("need-covered", "N-001")
    record_run(world)
    assert gatelib.evaluate(gate, world.ws)["open"]


@given("no MCP client")
def no_mcp_client(context):
    context.mcp_client = None


@when('I query the {subject} of gate "{gate}"')
def query_subject(context, subject, gate):
    key = subject.replace(" status", "").replace(" ", "-")
    context.subject = key
    context.cli_result = context.world.cli("audit", gate, key)
    context.result = json.loads(context.cli_result.stdout) if context.cli_result.stdout.strip() else None


@then("the result lists the matching records")
def lists_records(context):
    assert context.cli_result.returncode == 0, context.cli_result.stderr + context.cli_result.stdout
    r, ws = context.result, context.world.ws
    assert r == json.loads(json.dumps(audit.query("G3", context.subject, ws)))
    match context.subject:
        case "approvals":
            assert r and {x["gate"] for x in r} == {"G3"} and any(x["superseded"] for x in r) and any(not x["superseded"] for x in r)
        case "waivers":
            assert [w["element"] for w in r["valid"]] == ["N-001"] and not r["invalid"]
        case "changes":
            assert [c["who"] for c in r] == ["alice"] and r[0]["complete"] and r[0]["why"] == "clarify"
        case "test-evidence":
            assert r["run"]["current"] and r["requirements"]
        case "integrity":
            assert r["ok"] and r["gate"] == "G3"
