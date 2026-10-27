"""Steps of 06_approvals_gates.feature."""
import datetime

from behave import given, then, when

import approvals
import gate as gatelib
import specflow_core as core
import specrun
import tracecheck


def scenario_results(failing=0):
    """Recorded results for every real scenario of the world's specification; the first `failing` ones fail."""
    out = []
    for i, s in enumerate(tracecheck.load_scenarios()):
        out.append({"scenario": s["name"], "location": f"specs/features/{s['file']}:{s['line']}", "tags": s["tags"],
                    "status": "failed" if i < failing else "passed", "duration": 0.0, "detail": ""})
    return out


def record_run(world, failing=0):
    return specrun.record(world.ws, scenario_results(failing))


def approve_roles(context, gate, roles):
    for role in roles:
        context.world.approve(gate, role)
    if approvals.gates(context.world.ws)[gate].get("scenarios"):
        record_run(context.world)


def tag_field(world, tag, fmt):
    return core.git("tag", "--list", f"--format={fmt}", tag, cwd=world.root)


@when('the registered human "{signer}" with role "{role}" approves gate "{gate}" with rationale "{rationale}"')
def human_approves(context, signer, role, gate, rationale):
    context.world.approve(gate, role, signer, rationale)
    context.gate, context.role, context.signer, context.rationale = gate, role, signer, rationale
    context.tag = f"approval/{gate}/{role}.1"


@then('the signed tag "{tag}" exists')
def signed_tag_exists(context, tag):
    assert tag == f"approval/{context.gate}/{context.role}.1" == context.tag
    assert tag_field(context.world, context.tag, "%(objecttype)") == "tag"
    assert approvals.verify_tag(context.tag, context.world.ws).ok


@then("the tag signature identifies the approver and the date")
def tag_signature(context):
    v = approvals.verify_tag(context.tag, context.world.ws)
    assert v.ok and v.signer == context.signer, v
    date = datetime.datetime.fromisoformat(tag_field(context.world, context.tag, "%(taggerdate:iso-strict)"))
    assert date.date() == datetime.date.today(), date


@then("the tag message holds the rationale")
def tag_message(context):
    assert context.rationale in tag_field(context.world, context.tag, "%(contents)")


@then("the approval reports the content hash of the gate scope")
def approval_scope_hash(context):
    ws = context.world.ws
    entry = approvals.gate_status(context.gate, ws)["roles"][context.role]
    scope = tuple(approvals.gates(ws)[context.gate]["scope"])
    assert entry["scope_fingerprint"] == approvals.fingerprint(ws, "HEAD", scope)
    assert len(entry["scope_fingerprint"]) == 64


@given('"{signer}" approved gate "{gate}" as "{role}"')
def signer_approved(context, signer, gate, role):
    context.world.approve(gate, role, signer)
    context.gate, context.role = gate, role


@when('"{signer}" approves gate "{gate}" as "{role}" again')
def signer_approves_again(context, signer, gate, role):
    context.world.approve(gate, role, signer)


@then("the newer approval counts")
def newer_counts(context):
    entry = approvals.gate_status(context.gate, context.world.ws)["roles"][context.role]
    assert entry["valid"] and entry["revision"] == 2 and entry["tag"].endswith(".2"), entry


@then("the older approval remains in the history")
def older_remains(context):
    assert [rev for rev, _ in approvals.role_tags(context.world.ws, context.gate, context.role)] == [1, 2]
    assert approvals.verify_tag(f"approval/{context.gate}/{context.role}.1", context.world.ws).ok


@given('the gate "{gate}" requires the roles "{required}"')
def gate_requires(context, gate, required):
    context.gate_under_test = gate
    context.world.set_gate(gate, roles=[r.strip() for r in required.split(",")])
    assert context.world.roles_of(gate) == [r.strip() for r in required.split(",")]


@given('the roles "{approved}" hold valid approvals for the current content')
def roles_approved(context, approved):
    approve_roles(context, context.gate_under_test, [r.strip() for r in approved.split(",")])


@given('all required roles hold valid approvals for gate "{gate}"')
def all_roles_approved(context, gate):
    context.gate_under_test = gate
    approve_roles(context, gate, context.world.roles_of(gate))


@given("the trace rules report no unwaived gap")
def no_gap(context):
    assert not tracecheck.evaluate(("needs", "model", "spec"))["violations"]


@given("the trace rules report an unwaived gap")
def unwaived_gap(context):
    context.gap = context.world.make_gap()
    assert any(v["element"] == context.gap[1] for v in tracecheck.evaluate(("needs", "model", "spec"))["violations"])


@then("the gap is listed")
def gap_listed(context):
    rule, element = context.gap
    assert any(v["rule"] == rule and v["element"] == element for v in context.report["trace"]["violations"])
    assert any(element in p for p in context.report["problems"])


@given("a scenario of the specification fails")
def scenario_fails(context):
    payload = record_run(context.world, failing=1)
    assert payload["summary"]["failed"] == 1


@given("the required roles approved an earlier version of the model")
def approved_earlier(context):
    context.world.approve_all("G2")


@given("the model content has changed since")
def model_changed(context):
    context.world.edit_element("SR-004", "text changed after the approvals")
    context.world.commit("change SR-004")


@then("the approvals are reported as stale")
def reported_stale(context):
    st = context.report["approvals"]
    assert any("scope changed since approval" in p for p in context.report["problems"]), st["problems"]
    assert all(e["stale"] for e in st["roles"].values())


@when('the signer "{signer}" tries to approve gate "{gate}" as "{role}"')
@when('"{signer}" tries to approve gate "{gate}" as "{role}"')
def try_approve(context, signer, gate, role):
    try:
        context.world.approve(gate, role, signer)
        context.rejected = False
    except core.Rejected:
        context.rejected = True
    context.gate, context.role = gate, role
    tags = core.git("tag", "--list", f"approval/{gate}/*", cwd=context.world.root)
    assert bool(tags) is (not context.rejected), "a rejected approval must leave no tag"


@then("the approval is {outcome}")
def approval_outcome(context, outcome):
    assert context.rejected is {"accepted": False, "rejected": True}[outcome]


@given('"{signer}" is registered but not mapped to the role "{role}"')
def registered_not_mapped(context, signer, role):
    roles = context.world.read_json("approvals/roles.json")
    roles[signer] = [r for r in roles[signer] if r != role]
    context.world.write_json("approvals/roles.json", roles)
    assert (context.world.root / f"approvals/keys/{signer}.pub").exists() and role not in roles[signer]


@given('one person signed the approvals for all roles of gate "{gate}"')
def one_person_signed(context, gate):
    context.world.approve_all(gate, "alice")
    assert approvals.gate_status(gate, context.world.ws)["single_person"]


@when('I evaluate gate "{gate}" with single-person approval not allowed')
def evaluate_single_not_allowed(context, gate):
    context.world.set_single_person(False)
    context.report = gatelib.evaluate(gate, context.world.ws)


@when('I evaluate gate "{gate}" with single-person approval allowed in the gate configuration')
def evaluate_single_allowed(context, gate):
    context.world.set_single_person(True)
    context.report = gatelib.evaluate(gate, context.world.ws)


@then("the status reports single-person approval")
def reports_single(context):
    assert context.report["approvals"]["single_person"] is True


@then('the approvals of gate "{gate}" are reported as stale')
def gate_approvals_stale(context, gate):
    st = approvals.gate_status(gate, context.world.ws)
    assert not st["open"] and any("scope changed since approval" in p for p in st["problems"]), st["problems"]
    assert all(e["stale"] for e in st["roles"].values())


@then("all approval tags are retained")
def tags_retained(context):
    tags = core.git("tag", "--list", "approval/G2/*", cwd=context.world.root).split()
    assert len(tags) >= len(context.world.roles_of("G2"))
    assert all(approvals.verify_tag(t, context.world.ws).ok for t in tags)


@then('gate "{gate}" remains open')
def gate_remains_open(context, gate):
    rep = gatelib.evaluate(gate, context.world.ws)
    assert rep["open"], rep["problems"]


@given('the repository moves forward without changing the scope of gate "{gate}"')
def repository_moves_forward(context, gate):
    before = approvals.fingerprint(context.world.ws, "HEAD", tuple(approvals.gates(context.world.ws)[gate]["scope"]))
    context.world.commit("unrelated change")
    after = approvals.fingerprint(context.world.ws, "HEAD", tuple(approvals.gates(context.world.ws)[gate]["scope"]))
    assert before == after


@given('all roles of gate "{gate}" except "{role}" approved the current commit')
def others_approved(context, gate, role):
    for r in context.world.roles_of(gate):
        if r != role:
            context.world.approve(gate, r)
    context.approved_commit = context.world.git("rev-parse", "HEAD").stdout.strip()


@when('"{signer}" approves gate "{gate}" as "{role}" for the commit approved by the others')
def approve_earlier_commit(context, signer, gate, role):
    context.world.approve(gate, role, signer, commit=context.approved_commit)


@when('"{signer}" tries to approve gate "{gate}" as "{role}" for the commit approved by the others')
def try_approve_earlier_commit(context, signer, gate, role):
    try:
        context.world.approve(gate, role, signer, commit=context.approved_commit)
        context.rejected = False
    except core.Rejected:
        context.rejected = True
    assert not approvals.role_tags(context.world.ws, gate, role) or not context.rejected, "a rejected approval must leave no tag"


@when('the other roles of gate "{gate}" approve the same commit')
def others_approve_head(context, gate):
    for r in context.world.roles_of(gate):
        if r != context.role:
            context.world.approve(gate, r)


@then('the newest revision of gate "{gate}" is approved only by "{role}"')
def newest_revision_only(context, gate, role):
    context.gate, context.role = gate, role
    revision = approvals.gate_status(gate, context.world.ws)["revision"]
    assert revision["commit"] == context.world.git("rev-parse", "HEAD").stdout.strip(), revision
    assert revision["approved"] == [role], revision


@then('the report lists the other roles of gate "{gate}" as still missing')
def others_missing(context, gate):
    revision = approvals.gate_status(gate, context.world.ws)["revision"]
    assert revision["missing"] == [r for r in context.world.roles_of(gate) if r != context.role], revision
    assert any("different commits" in p for p in context.report["problems"]), context.report["problems"]
