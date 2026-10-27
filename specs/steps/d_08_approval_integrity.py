import os
import re
import shutil
import stat
import subprocess

from behave import given, then, when

import approvals
import audit
import coverage_report
import tracecheck
from d_mcp_helpers import SERVERS, call, list_tools
from world import CODE_ROOT, sh

STAGES = ("needs", "model", "spec")


# --- invalid approval tags ---------------------------------------------------

@when('the approval tag "{tag}" is {manipulation}')
def manipulate_tag(context, tag, manipulation):
    w = context.world
    gate, role = tag.split("/")[1:3]
    for _rev, old in approvals.role_tags(w.ws, gate, role):
        w.git("tag", "-d", old)
    if manipulation == "replaced by an unsigned tag":
        w.git("tag", "-a", tag, "-m", "unsigned approval")
    elif manipulation == "replaced by a tag of an unregistered key":
        w.use_key("mallory")
        try:
            w.git("tag", "-s", tag, "-m", "approval by an unregistered key")
        finally:
            w.use_key("alice")
    else:
        raise AssertionError(manipulation)
    context.tag = tag


@when('I verify gate "{gate}"')
def verify_gate(context, gate):
    w = context.world
    context.gate = gate
    context.status = context.report = approvals.gate_status(gate, w.ws)
    context.integrity = audit.integrity(gate, w.ws)
    cli = w.cli("audit", gate, "integrity")
    context.integrity_cli_exit = cli.returncode


@then('the verification reports an invalid approval for the role "{role}"')
def reports_invalid(context, role):
    entry = context.status["roles"][role]
    assert not entry["valid"] and entry["reason"], entry
    assert entry["tag"] == context.tag, entry
    assert not context.integrity["ok"] and context.tag in context.integrity["invalid_current_approvals"], context.integrity
    assert context.integrity_cli_exit != 0


# --- waivers -----------------------------------------------------------------

@given("a trace gap that is waived by a signed waiver tag with {condition}")
def invalid_waiver(context, condition):
    w = context.world
    rule, element = w.make_gap()
    kwargs = {"no rationale": {"rationale": ""},
              "a past expiry date": {"expiry": "2020-01-01"},
              "an unregistered signer": {"signer": "mallory"}}[condition]
    context.gap = (rule, element)
    context.waiver_tag = w.sign_waiver(rule, element, **kwargs)


@given("a trace gap that is waived by a valid signed waiver tag")
def valid_waiver(context):
    w = context.world
    rule, element = w.make_gap()
    context.gap = (rule, element)
    context.waiver_tag = w.sign_waiver(rule, element, rationale="accepted for this iteration")


@when("I evaluate the trace rules")
def evaluate_trace(context):
    context.trace = tracecheck.evaluate(STAGES)


@then("the waiver is ignored")
def waiver_ignored(context):
    rule, element = context.gap
    t = context.trace
    assert not [x for x in t["waivers"] if (x["rule"], x["element"]) == (rule, element)], t["waivers"]
    assert [x for x in t["invalid_waivers"] if x["tag"] == context.waiver_tag and x["reason"]], t["invalid_waivers"]
    assert not t["waived"], t["waived"]


@then("the gap is reported")
def gap_reported(context):
    rule, element = context.gap
    assert [v for v in context.trace["violations"] if (v["rule"], v["element"]) == (rule, element)], context.trace["violations"]


@when("I generate the coverage report")
def coverage(context):
    context.coverage = coverage_report.build()
    context.coverage_md = coverage_report.markdown(context.coverage)


@then("the waiver is listed with its rationale and expiry")
def waiver_listed(context):
    rule, element = context.gap
    listed = [x for x in context.coverage["waivers"] if (x["rule"], x["element"]) == (rule, element)]
    assert len(listed) == 1 and listed[0]["rationale"] and listed[0]["expiry"], context.coverage["waivers"]
    line = next(l for l in context.coverage_md.splitlines() if f"{rule} {element}" in l and "expires" in l)
    assert listed[0]["rationale"] in line and listed[0]["expiry"] in line, line
    assert not [v for v in context.coverage["violations"] if (v["rule"], v["element"]) == (rule, element)]


# --- drift -------------------------------------------------------------------

@when("a file of the gate scope is modified without a new approval")
def modify_scope_file(context):
    w = context.world
    gate = next(g for g in approvals.gates(w.ws) if w.git("tag", "--list", f"approval/{g}/*").stdout.split())
    scope = approvals.gates(w.ws)[gate]["scope"]
    target = next(p for s in scope for p in sorted((w.root / s).rglob("*") if (w.root / s).is_dir() else [w.root / s])
                  if p.is_file())
    target.write_text(target.read_text(encoding="utf-8") + "\n// unapproved change\n", encoding="utf-8")
    context.modified = target.relative_to(w.root).as_posix()


@then("the verification reports the differing files of the gate scope")
def reports_drift(context):
    assert context.status["drift"] == [context.modified], context.status["drift"]
    assert context.integrity["drift"] == [context.modified] and not context.integrity["ok"], context.integrity
    assert not context.status["open"]


# --- agent identity and approval refs ---------------------------------------

def _push(w, host, *refspec):
    r = subprocess.run(["git", "push", str(host), *refspec], cwd=w.root, capture_output=True, text=True,
                       env={**os.environ, "SPECFLOW_KEYS_DIR": str(w.root / "approvals/keys")}, check=False)
    return r.returncode, r.stderr


@given("the agent identity")
def agent_identity(context):
    w = context.world
    assert "agent-1" in w.read_json("approvals/roles.json") and not w.read_json("approvals/roles.json")["agent-1"]
    host = w.dir / "host.git"
    sh(w.dir, "git", "init", "-q", "--bare", str(host))
    hook = host / "hooks/pre-receive"
    shutil.copy(CODE_ROOT / "tools/hooks/pre-receive", hook)
    hook.chmod(hook.stat().st_mode | stat.S_IXUSR)
    sh(w.root, "git", "push", "-q", str(host), "main")
    context.host = host


@when("it tries to push to an approval or waiver ref")
def agent_pushes(context):
    w, host = context.world, context.host
    w.git("tag", "-a", "approval/G2/reviewer.1", "-m", "unsigned")
    w.git("tag", "-a", "waiver/need-covered/N-001.1", "-m", "rationale: x\nexpiry: 2999-01-01")
    w.use_key("mallory")
    w.git("tag", "-s", "approval/G2/reviewer.2", "-m", "unregistered key")
    w.git("tag", "approval/G2/reviewer.3")
    w.use_key("alice")
    w.git("tag", "-s", "approval/G2/reviewer.4", "-m", "registered key")
    context.attempts = {
        "unsigned annotated tag": _push(w, host, "refs/tags/approval/G2/reviewer.1"),
        "unsigned waiver tag": _push(w, host, "refs/tags/waiver/need-covered/N-001.1"),
        "tag of an unregistered key": _push(w, host, "refs/tags/approval/G2/reviewer.2"),
        "lightweight tag": _push(w, host, "refs/tags/approval/G2/reviewer.3"),
    }
    context.control = _push(w, host, "refs/tags/approval/G2/reviewer.4")
    context.attempts["deletion of an existing approval tag"] = _push(w, host, ":refs/tags/approval/G2/reviewer.4")
    context.attempts["move of an existing approval tag"] = _push(w, host, "-f", "refs/tags/approval/G2/reviewer.1:refs/tags/approval/G2/reviewer.4")


@then("the push is rejected by the repository host or hook")
def push_rejected(context):
    for what, (code, err) in context.attempts.items():
        assert code != 0 and "rejected refs/tags" in err, (what, err)
    refs = sh(context.host, "git", "--git-dir", str(context.host), "tag", "--list").stdout.split()
    assert refs == ["approval/G2/reviewer.4"], refs


@then("the rejection does not depend on the checks of the servers")
def hook_independent(context):
    code, err = context.control
    assert code == 0, err  # the hook accepts a valid signature, so the rejections above are decided by signature checks
    source = (CODE_ROOT / "tools/hooks/pre-receive").read_text(encoding="utf-8")
    assert not re.search(r"^\s*(import|from)\s+(specflow_core|mcp\w*|approvals|gate)\b", source, re.MULTILINE)
    assert not (context.host / "tools").exists()


# --- agent-facing tools ------------------------------------------------------

@given("the agent-facing tools of the servers")
def agent_tools(context):
    context.tool_defs = {name: list_tools(server) for name, server in SERVERS.items()}


@when("I list them")
def list_them(context):
    context.tags_before = context.world.git("tag", "--list").stdout
    context.listed = {(s, t.name): t for s, tools in context.tool_defs.items() for t in tools}
    assert context.listed


@then("none of them creates, moves or deletes an approval or waiver ref")
def no_ref_tools(context):
    pattern = r"approv|waiv|\btags?\b|\bref\b|\bsign"
    related = {n for (_s, n), t in context.listed.items()
               if re.search(pattern, n, re.IGNORECASE) or re.search(r"approval (tag|ref)|waiver|\bsigns?\b", t.description, re.IGNORECASE)}
    assert related == {"approval_status"}, related
    ref_params = {"tag", "ref", "role", "gate", "signature", "key", "branch"}
    for (_s, name), t in context.listed.items():
        props = set((t.input_schema or {}).get("properties", {}))
        if name == "approval_status":
            assert not props and "Read-only" in t.description, (props, t.description)
        else:
            assert not (props & (ref_params - {"branch"})), (name, props)
    for server in SERVERS.values():
        err, _text = call(server, "approval_status", {})
        assert not err
    assert context.world.git("tag", "--list").stdout == context.tags_before
    # propose_edit is the only tool that names a git ref; it is restricted to proposal/* branches
    err, text = call(SERVERS["model"], "propose_edit", {"path": "inputs.txt", "content": "x", "branch": "approval/G2/x", "message": "m"})
    assert err and "proposal/" in text, text
    assert context.world.git("tag", "--list").stdout == context.tags_before
