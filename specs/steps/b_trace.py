"""Steps of 04_trace.feature, bound to tools/tracecheck.py, tools/gate.py, tools/waivers.py and tools/coverage_report.py."""
import datetime
import os
import re
import subprocess
import sys

from behave import given, then, when

import approvals
import coverage_report
import specflow_core as core
import tracecheck
import waivers
from b_support import (drop_dependencies, drop_satisfy, drop_scenario_tag, tag_first_scenario, untag_first_scenario)

MODEL_DEFECTS = [
    (r"need (N-\d+) is covered by no use case", lambda w, e: drop_dependencies(w, rf"UC-\d+ covers {e}")),
    (r"use case (UC-\d+) exercises no requirement", lambda w, e: drop_dependencies(w, rf"{e} exercises [^']*")),
    (r"requirement (SR-\d+) derives from no need", lambda w, e: drop_dependencies(w, rf"{e} derives N-\d+")),
    (r"requirement (DR-\d+) derives from no L1 requirement", lambda w, e: drop_dependencies(w, rf"{e} derives SR-\d+")),
    (r"requirement (DR-\d+) is allocated to no element", drop_satisfy),
]


def apply_defect(world, defect, table):
    for pattern, action in table:
        m = re.fullmatch(pattern, defect)
        if m:
            assert action(world, m.group(1)), f"defect '{defect}' changed nothing"
            world.commit(defect)
            return m.group(1)
    raise AssertionError(f"unknown defect: {defect}")


@given("a model in which {defect}")
def model_defect(context, defect):
    apply_defect(context.world, defect, MODEL_DEFECTS)


@given("a specification in which {defect}")
def spec_defect(context, defect):
    w = context.world
    if m := re.fullmatch(r"requirement (SR-\d+) has no scenario", defect):
        assert drop_scenario_tag(w, m.group(1)), "no scenario was tagged with the requirement"
    elif m := re.fullmatch(r"a scenario is tagged with unknown @(SR-\d+)", defect):
        assert m.group(1) not in tracecheck.load_model()[0]
        assert tag_first_scenario(w, m.group(1))
    elif defect == "a scenario has no ID tag":
        context.scenario_location = untag_first_scenario(w)
    else:
        raise AssertionError(f"unknown defect: {defect}")
    w.commit(defect)


@when('I run the trace check for stage "{stage}"')
def run_trace_check(context, stage):
    context.trace = tracecheck.evaluate((stage,))


@then('the report contains a violation of rule "{rule}" for the element "{element}"')
def violation_present(context, rule, element):
    if element == "the scenario":
        element = context.scenario_location
    hits = [v for v in context.trace["violations"] if v["rule"] == rule and v["element"] == element]
    assert hits, f"no {rule} violation for {element}: {context.trace['violations']}"


@then("the report contains no violations")
def no_violations(context):
    assert context.trace["violations"] == [], context.trace["violations"]


# --- gates and waivers -------------------------------------------------------

@given("a trace report with an unwaived gap")
def unwaived_gap(context):
    context.gap = context.world.make_gap()
    assert context.gap in {(v["rule"], v["element"]) for v in tracecheck.evaluate(("needs",))["violations"]}


@given("all required roles have approved")
def all_roles_approved(context):
    for gate in ("G2", "G3"):
        context.world.approve_all(gate)
        assert approvals.gate_status(gate, context.world.ws)["open"], "approvals alone must open the gate"


@then("the reason lists the gap")
def reason_lists_gap(context):
    rule, element = context.gap
    assert any(rule in p and element in p for p in context.report["problems"]), context.report["problems"]


@given("a trace report with a gap waived by a signed waiver with approver, rationale and expiry")
def waived_gap(context):
    context.gap = context.world.make_gap()
    context.waiver_tag = context.world.sign_waiver(*context.gap)
    valid, invalid = waivers.load(context.world.ws)
    mine = [w for w in valid if w["tag"] == context.waiver_tag]
    assert mine and mine[0]["approver"] == "alice" and mine[0]["rationale"] and mine[0]["expiry"], (valid, invalid)


@then("every report lists the waiver")
def reports_list_waiver(context):
    rule, element = context.gap
    tag = context.waiver_tag

    def lists(entries):
        return any(w["tag"] == tag and w["rule"] == rule and w["element"] == element for w in entries)

    assert lists(context.report["trace"]["waivers"]), "gate report"
    assert any(x["rule"] == rule and x["element"] == element for x in context.report["trace"]["waived"]), "gate report waived gap"
    result = tracecheck.evaluate(("needs", "model", "spec"))
    assert lists(result["waivers"]) and result["waived"], "trace report"
    report = coverage_report.build()
    assert lists(report["waivers"]), "coverage report"
    assert f"- {rule} {element}:" in coverage_report.markdown(report), "coverage report (markdown)"


INVALID_WAIVERS = {
    "without a rationale": ({"rationale": ""}, "no rationale"),
    "whose expiry has passed": ({"expiry": (datetime.date.today() - datetime.timedelta(days=1)).isoformat()},
                                "expiry missing or in the past"),
    "signed by the agent": ({"signer": "agent-1"}, "signed by an agent identity"),
}


@given("a trace report with a gap and a waiver {problem}")
def gap_with_invalid_waiver(context, problem):
    kwargs, reason = INVALID_WAIVERS[problem]
    context.gap = context.world.make_gap()
    tag = context.world.sign_waiver(*context.gap, **kwargs)
    valid, invalid = waivers.load(context.world.ws)
    assert not [w for w in valid if w["tag"] == tag]
    assert [w for w in invalid if w["tag"] == tag and w["reason"] == reason], invalid
    for gate in ("G2",):
        context.world.approve_all(gate)


# --- queries, references, determinism ------------------------------------------

@when('I query the trace from "{src}" to "{dst}"')
def query_trace(context, src, dst):
    context.query = tracecheck.query(src, dst)


@then("the result lists the connected elements")
def query_result(context):
    q = context.query
    assert q["connected"], f"nothing connects {q['from']} to {q['to']}"
    edges = {frozenset((a, b)) for a, _v, b in tracecheck.graph()["edges"]}
    for node, path in q["paths"].items():
        assert path[-1] == node
        assert all(frozenset(pair) in edges for pair in zip(path, path[1:])), path
        if q["from"] != "scenario":
            assert path[0] == q["from"]
        if q["to"] == "scenario":
            assert ".feature:" in node
        else:
            assert node == q["to"]


@given('an approved link to element "{element}"')
def approved_link(context, element):
    w = context.world
    _ids, links, _alloc = tracecheck.load_model()
    assert any(element in (a, b) for a, _v, b in links), f"no link refers to {element}"
    w.approve_all("G2")
    assert tracecheck.reference_findings(w.ws) == []


@when('the element "{element}" is removed')
def remove_element(context, element):
    import arch
    w = context.world
    for f in sorted((w.root / "model").glob("*.sysml")):
        text = f.read_text(encoding="utf-8")
        m = re.search(rf"requirement\s+<'{element}'>\s+\w+[^{{]*", text)
        if m:
            end = m.end() + len(arch.block(text, m.end() - 1)) + 2
            f.write_text(text[:m.start()] + text[end:], encoding="utf-8")
            w.commit(f"remove {element}")
            return
    raise AssertionError(f"element {element} not found")


@then('the trace check reports a {kind} reference to "{element}"')
def reference_reported(_, kind, element):
    rule = {"dangling": "link-dangling", "stale": "link-stale"}[kind]
    found = tracecheck.evaluate(("refs",))["violations"]
    assert any(v["rule"] == rule and v["element"] == element for v in found), found
    assert all(not (v["rule"] == other and v["element"] == element) for v in found
               for other in {"link-dangling", "link-stale"} - {rule}), found


@when("I build the trace graph twice")
def build_graph_twice(context):
    code = "import sys; sys.path.insert(0, %r); import tracecheck; sys.stdout.write(tracecheck.graph_json())" % str(core.CODE_ROOT / "tools")
    context.serialisations = [tracecheck.graph_json()]
    for seed in ("1", "2"):
        r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                           env={**os.environ, "PYTHONHASHSEED": seed}, check=False)
        assert r.returncode == 0, r.stderr
        context.serialisations.append(r.stdout)


@then("both serialisations are byte-identical")
def graph_identical(context):
    first, *rest = (s.encode("utf-8") for s in context.serialisations)
    assert first and all(r == first for r in rest)
