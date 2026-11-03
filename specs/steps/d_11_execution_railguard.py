"""Steps of 11_execution_railguard.feature."""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from behave import given, then, when

import exectrace

CODE_ROOT = Path(__file__).resolve().parents[2]
ENTERED = "tools/exectrace.py:load_allowlist"


def workdir(context):
    if not hasattr(context, "rail_dir"):
        context.rail_dir = tempfile.TemporaryDirectory(prefix="specflow-rail-")
        context.add_cleanup(context.rail_dir.cleanup)
        context.rail = {"functions": set(), "executed": None, "entries": []}
    return Path(context.rail_dir.name)


@given('an implementation with the functions "{a}" and "{b}"')
def implementation(context, a, b):
    workdir(context)
    context.rail["functions"] = {a, b}


@given('an execution trace that entered only "{fn}"')
def trace_entered(context, fn):
    workdir(context)
    context.rail["executed"] = [fn]


@given("no execution trace was recorded")
def no_trace(context):
    workdir(context)
    context.rail["executed"] = None


@given('an allowlist entry for "{fn}" with the reason "{reason}"')
def allowlist_with_reason(context, fn, reason):
    workdir(context)
    context.rail["entries"].append({"function": fn, "reason": reason})


@given('an allowlist entry for "{fn}" without a reason')
def allowlist_without_reason(context, fn):
    workdir(context)
    context.rail["entries"].append({"function": fn, "reason": " "})


@when("the railguard check is evaluated")
def evaluate(context):
    root = workdir(context)
    (root / "specs").mkdir(exist_ok=True)
    (root / exectrace.ALLOWLIST).write_text(json.dumps({"entries": context.rail["entries"]}), encoding="utf-8")
    context.report = exectrace.report(context.rail["executed"], root, context.rail["functions"])


@then("the check fails")
def check_fails(context):
    assert context.report["problems"], context.report


@then("the check passes")
def check_passes(context):
    assert not context.report["problems"], context.report["problems"]


@then('the report names "{fn}" as never executed')
def names_unexecuted(context, fn):
    assert fn in context.report["unexecuted"], context.report


@then('the report lists "{fn}" as allowlisted')
def lists_allowlisted(context, fn):
    assert fn in context.report["allowlisted"], context.report


@then("the report contains a problem about an entry without a reason")
def problem_no_reason(context):
    assert any("without a reason" in p for p in context.report["problems"]), context.report["problems"]


@then("the report contains a problem about a missing execution trace")
def problem_no_trace(context):
    assert not context.report["traced"]
    assert any("no execution trace" in p for p in context.report["problems"]), context.report["problems"]


@given("a trace directory for a spec run")
def trace_directory(context):
    context.trace_dir = workdir(context) / "trace"


@when("a subprocess of the spec run enters a function of the implementation")
def subprocess_enters(context):
    code = "import exectrace, tempfile; exectrace.load_allowlist(tempfile.gettempdir())"
    env = {**os.environ, "SPECFLOW_TRACE_DIR": str(context.trace_dir), "PYTHONPATH": str(CODE_ROOT / "tools")}
    subprocess.run([sys.executable, "-c", code], env=env, check=True, capture_output=True)


@then("the merged execution trace contains that function")
def merged_contains(context):
    assert ENTERED in (exectrace.merge(context.trace_dir) or []), exectrace.merge(context.trace_dir)
