"""Steps of 05_coverage_and_run.feature, bound to tools/coverage_report.py, tools/specrun.py and the specflow CLI."""
import json
import os
import re
import subprocess
import sys

from behave import given, then, when

import approvals
import coverage_report
import specrun
from b_support import drop_scenario_tag, model_files, rewrite, synthetic_spec

LEVEL_WORDS = ("need", "use case", "requirement", "design element", "scenario")


@given('a model and a specification with one uncovered requirement "{req}"')
def uncovered_requirement(context, req):
    assert drop_scenario_tag(context.world, req)
    context.world.commit(f"no scenario for {req}")
    context.uncovered = req


@when("I produce the coverage report")
def produce_report(context):
    context.coverage = coverage_report.build()


@then("the report has a summary for each level need, use case, requirement, design element and scenario")
def levels_summarised(context):
    levels = [r["level"] for r in context.coverage["levels"]]
    for word in LEVEL_WORDS:
        rows = [r for r in context.coverage["levels"] if re.search(rf"\b{word}\b", r["level"])]
        assert rows and all(r["total"] > 0 and 0 <= r["covered"] <= r["total"] for r in rows), (word, levels)


@then("the report has a summary for each gate")
def gates_summarised(context):
    configured = set(approvals.gates(context.world.ws))
    assert configured and set(context.coverage["gates"]) == configured
    for row in context.coverage["gates"].values():
        assert {"stages", "open_violations", "waived", "trace_status"} <= set(row)


@then('the report lists "{element}" as a gap')
def lists_gap(context, element):
    assert any(element in r["gaps"] for r in context.coverage["levels"]), context.coverage["levels"]
    assert any(v["element"] == element for v in context.coverage["violations"])
    assert any(row["trace_status"] == "gaps" for row in context.coverage["gates"].values())


@when('I produce the coverage report as "{fmt}"')
def produce_report_as(context, fmt):
    w = context.world
    context.coverage_format = fmt
    context.coverage_texts = []
    for n, seed in enumerate(("1", "2")):
        out = f"coverage_{n}.out"
        old = os.environ.get("PYTHONHASHSEED")
        os.environ["PYTHONHASHSEED"] = seed
        try:
            r = w.cli("coverage", "--format", fmt, "--out", out)
        finally:
            os.environ.pop("PYTHONHASHSEED") if old is None else os.environ.__setitem__("PYTHONHASHSEED", old)
        assert r.returncode == 0, r.stdout + r.stderr
        context.coverage_texts.append((w.root / out).read_text(encoding="utf-8"))


@then("the report is written in stable order")
def stable_order(context):
    a, b = context.coverage_texts
    assert a == b and a.strip()
    if context.coverage_format == "json":
        data = json.loads(a)
        assert a == json.dumps(data, indent=2, sort_keys=True) + "\n"
        assert all(r["gaps"] == sorted(r["gaps"]) for r in data["levels"])
    else:
        assert a.startswith("# Coverage report") and "## Levels" in a and "## Gates" in a
        gate_rows = re.findall(r"^\| (G\d) \|", a, re.M)
        assert gate_rows == sorted(gate_rows) and gate_rows


# --- spec execution ------------------------------------------------------------

@given('a specification with scenarios tagged "{first}" and "{second}"')
def tagged_scenarios(context, first, second):
    synthetic_spec(context.world, [(first, "passing"), (second, "passing")])
    context.expected_tags = [[first.lstrip("@")], [second.lstrip("@")]]


@given('a specification with a failing scenario tagged "{tag}"')
def failing_scenario(context, tag):
    synthetic_spec(context.world, [(tag, "failing")])


@when("I run the specification headless")
def run_headless(context):
    context.results = specrun.run(context.world.ws)


@then("the result contains one entry per scenario")
def one_entry_per_scenario(context):
    entries = context.results["scenarios"]
    assert len(entries) == len(context.expected_tags), entries
    assert len({e["location"] for e in entries}) == len(entries)
    assert specrun.load(context.world.ws) == context.results


@then("each entry has the ID tags, a status and a duration")
def entries_complete(context):
    entries = sorted(context.results["scenarios"], key=lambda e: e["location"])
    assert [e["tags"] for e in entries] == context.expected_tags
    for e in entries:
        assert e["status"] == "passed", e
        assert isinstance(e["duration"], float) and e["duration"] >= 0, e


@then('the failing scenario is reported with the requirement "{req}"')
def failing_reported(context, req):
    entries = context.results["scenarios"]
    assert len(entries) == 1
    assert entries[0]["status"] == "failed" and entries[0]["tags"] == [req] and entries[0]["detail"], entries
    assert context.results["summary"] == {"failed": 1}


# --- CLI -------------------------------------------------------------------------

def break_syntax(world):
    f = model_files(world)[0]
    assert rewrite([f], lambda t: t + "\npackage Broken { part def ; ;; }}} {{\n")
    world.commit("syntax error")


FAILURES = {
    "the model has a syntax error": break_syntax,
    "the trace has a gap": lambda w: w.make_gap(),
    "a scenario fails": lambda w: synthetic_spec(w, [("@SR-004", "failing")]),
    "a gate has unmet conditions": lambda w: None,
}


@given("a workspace in which {failure}")
def workspace_failure(context, failure):
    FAILURES[failure](context.world)


@when('I run the CLI command "{command}"')
def run_cli(context, command):
    args = ("gate", "G2") if command == "gate" else (command,)
    context.cli_result = context.world.cli(*args)


@then("the exit code is not zero")
def exit_code_nonzero(context):
    r = context.cli_result
    assert r.returncode == 1, (r.returncode, r.stdout, r.stderr)
    assert "Traceback" not in r.stderr, r.stderr


def commands(world):
    out = []
    for args in (("validate", "--json"), ("trace", "--json"), ("coverage", "--format", "json")):
        r = world.cli(*args)
        out.append((args[0], r.returncode, r.stdout))
    return out


@when("I run validation, the trace check and the coverage report twice")
def run_twice(context):
    context.runs = [commands(context.world) for _ in range(2)]


@then("the results of both runs are identical")
def runs_identical(context):
    first, second = context.runs
    assert first == second
    assert all(code == 0 and out.strip() for _n, code, out in first), first


NO_NETWORK = '''import socket


def _refuse(*args, **kwargs):
    raise OSError("network access is disabled in this test")


_connect = socket.socket.connect


def _connect_local_only(self, address):
    if self.family in (socket.AF_INET, socket.AF_INET6):
        _refuse()
    return _connect(self, address)


socket.socket.connect = _connect_local_only
socket.create_connection = _refuse
socket.getaddrinfo = _refuse
'''


@given("no MCP client and no network access")
def no_network(context):
    d = context.world.dir / "nonet"
    d.mkdir()
    (d / "sitecustomize.py").write_text(NO_NETWORK, encoding="utf-8")
    old = os.environ.get("PYTHONPATH")
    os.environ["PYTHONPATH"] = str(d) + (os.pathsep + old if old else "")

    def restore():
        os.environ.pop("PYTHONPATH") if old is None else os.environ.__setitem__("PYTHONPATH", old)

    context.add_cleanup(restore)
    probe = subprocess.run([sys.executable, "-c", "import socket; socket.create_connection(('127.0.0.1', 9))"],
                           capture_output=True, text=True)
    assert "network access is disabled" in probe.stderr, probe.stderr


@when("I run validation, the trace check and the coverage report")
def run_once(context):
    context.runs = [commands(context.world)]


@then("all commands complete successfully")
def commands_succeed(context):
    (results,) = context.runs
    assert [n for n, _c, _o in results] == ["validate", "trace", "coverage"]
    assert all(code == 0 and out.strip() for _n, code, out in results), results
