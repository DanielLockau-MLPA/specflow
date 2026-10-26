"""Steps of 02_model_validation.feature."""
import json
import os
import re
import sys

from behave import given, then, when

import a_mcp

ALT_BACKEND = '''def backend(docs):
    first = sorted(docs)[0]
    return [{"file": first, "line": 1, "column": 1, "severity": "info", "code": "alt", "message": "alternative backend"}]
'''


def sr004_file(context):
    for f in sorted((context.world.root / "model").glob("*.sysml")):
        if "<'SR-004'>" in f.read_text(encoding="utf-8"):
            return f
    raise AssertionError("SR-004 not found")


def validate(context, env=None):
    saved = dict(os.environ)
    os.environ.update(env or {})
    try:
        r = context.world.cli("validate", "--json")
    finally:
        os.environ.clear()
        os.environ.update(saved)
    assert r.returncode in (0, 1), r.stdout + r.stderr
    return json.loads(r.stdout)


@given("a model file containing a syntax error in {element}")
def syntax_error(context, element):
    f = sr004_file(context)
    text = f.read_text(encoding="utf-8")
    header = re.search(rf"requirement\s+<'{element}'>[^{{]*\{{\n", text)
    f.write_text(text[:header.end()] + "        attribute ;; broken\n" + text[header.end():], encoding="utf-8")
    context.defect = (element, "syntax")


@given("a model file containing a requirement without a doc")
def undocumented(context):
    f = sr004_file(context)
    text = f.read_text(encoding="utf-8")
    new = re.sub(r"(requirement\s+<'SR-004'>[^{]*\{\n)\s*doc /\*.*?\*/\n", r"\1", text, count=1, flags=re.S)
    assert new != text
    f.write_text(new, encoding="utf-8")
    context.defect = ("SR-004", "requirement-doc")


@given('a configured parser backend "alternative"')
def alternative_backend(context):
    (context.world.root / "alt_backend.py").write_text(ALT_BACKEND, encoding="utf-8")
    context.env = {"SPECFLOW_PARSER_BACKEND": "alt_backend:backend", "PYTHONPATH": str(context.world.root)}


@when("I validate the model")
def validate_model(context):
    context.validation = validate(context, getattr(context, "env", None))


@then('the report contains a finding with severity "{severity}"')
def has_severity(context, severity):
    element, code = context.defect
    context.finding = next((f for f in context.validation["findings"]
                            if f["severity"] == severity and f["element"] == element and f["code"] == code), None)
    assert context.finding, [f for f in context.validation["findings"] if f["element"] == element]


@then("the finding names the file, the line and the element ID")
def finding_location(context):
    f = context.finding
    assert f["file"].endswith(".sysml") and (context.world.root / f["file"]).is_file()
    assert isinstance(f["line"], int) and f["line"] > 0
    assert f["element"] == context.defect[0]
    lines = (context.world.root / f["file"]).read_text(encoding="utf-8").splitlines()
    assert f["line"] <= len(lines)


@then('the report contains no findings with severity "{severity}"')
def no_severity(context, severity):
    assert not [f for f in context.validation["findings"] if f["severity"] == severity]


@then("the report has the same structure as for the default backend")
def same_structure(context):
    alt = context.validation
    context.env = {}
    default = validate(context)
    assert any(f["code"] == "alt" for f in alt["findings"]) and not any(f["code"] == "alt" for f in default["findings"])
    assert alt.keys() == default.keys() and alt["files"] == default["files"]
    keys = {frozenset(f) for f in alt["findings"]} | {frozenset(f) for f in default["findings"]}
    assert len(keys) == 1, keys


@when("an MCP client lists the tools of the {server} server")
def list_tools(context, server):
    context.tools = a_mcp.tool_names(server)


@then("the tools include {names}")
def tools_include(context, names):
    for name in re.findall(r'"(\w+)"', names):
        assert any(t == name or t.startswith(name + "_") for t in context.tools), (name, context.tools)


@when('an MCP client reads the element "{element}"')
def read_element(context, element):
    error, text = a_mcp.call("model", "read_element", {"element_id": element})
    assert not error, text
    context.element = json.loads(text)


@then("the result contains the element text and its kind")
def element_result(context):
    e = context.element
    assert e["kind"] == "SR" and e["text"] and "validate" in e["text"]


@when('an MCP client searches for "{query}"')
def search(context, query):
    error, text = a_mcp.call("model", "search", {"query": query})
    assert not error, text
    context.found = text


@then('the result lists "{element}"')
def result_lists(context, element):
    assert f'"{element}"' in context.found
