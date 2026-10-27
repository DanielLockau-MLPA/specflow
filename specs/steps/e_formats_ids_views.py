"""Steps for 10_formats_ids_views.feature: open formats, ID scheme, Mermaid export, diff-ability, MCP clients."""
import asyncio
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from behave import given, then, when

import arch
import ids
import specflow_core as core
from world import CODE_ROOT

OPEN_EXTENSIONS = {".sysml", ".feature", ".yaml", ".json", ".md"}
# trust-anchor public keys in approvals/keys/ are key material, not artifacts
ARTIFACT_SPECS = ("model/", "specs/features/", "decisions/", "trace/", "approvals/*.json")


@when("I list all persistent artifacts of the project")
def list_artifacts(context):
    w = context.world
    context.artifacts = [p for p in w.git("ls-files", "--", *ARTIFACT_SPECS).stdout.splitlines() if p]
    assert context.artifacts, "no persistent artifacts found"


# comment by DL: I think that yaml slipped in here by accident. Please trace back where this comes from and whether it is justified.
@then('every artifact has one of the extensions ".sysml", ".feature", ".yaml", ".json" or ".md", except public key files under "approvals/keys"')
def artifacts_open(context):
    bad = [a for a in context.artifacts if Path(a).suffix not in OPEN_EXTENSIONS]
    assert not bad, f"artifacts with non-open formats: {bad}"


@when("the files are opened with a plain text editor")
def open_plain(context):
    context.texts = {}
    for f in sorted((context.world.root / "model").glob("*.sysml")):
        context.texts[f.name] = f.read_bytes().decode("utf-8")  # plain UTF-8 decoding, no toolchain


@then("the requirements and their IDs are readable")
def requirements_readable(context):
    text = "\n".join(context.texts.values())
    found = set(re.findall(r"requirement <'((?:N|UC|SR|DR)-\d+)'>\s+\w+", text))
    assert {"SR-004", "DR-028"} <= found, found
    assert re.search(r"requirement <'SR-004'> ValidateModel[^{]*\{\s*doc\s*/\*\s*\S", text), "requirement text not readable"


@when('the ID "{new_id}" is registered for a new element')
def register_id(context, new_id):
    context.new_id = new_id
    context.reason = ids.check_new_id(new_id, context.world.ws)


@then("the registration is {outcome}")
def registration_outcome(context, outcome):
    assert outcome in ("accepted", "rejected"), outcome
    assert (context.reason is None) == (outcome == "accepted"), f"{context.new_id}: {context.reason}"


@given('the element "{element}" with the name "{name}"')
def element_with_name(context, element, name):
    context.element = element
    context.name = name
    assert core.model_ids(context.world.ws)[element][0] == name


@when('the element is renamed to "{new_name}"')
def rename_element(context, new_name):
    pattern = re.compile(rf"\b{re.escape(context.name)}\b")
    for f in (context.world.root / "model").glob("*.sysml"):
        text = f.read_text(encoding="utf-8")
        f.write_text(pattern.sub(new_name, text), encoding="utf-8")
    context.world.commit("rename element")
    context.name = new_name


@then('the element is still found by the ID "{element}"')
def found_by_id(context, element):
    name = core.model_ids(context.world.ws)[element][0]
    assert name == context.name, name


@when("the element is deleted")
def delete_element(context):
    # comment by DL: will this also work for the last element registered? -> this should be added as a scenario to check the implementation for robustness
    root = context.world.root
    for f in (root / "model").glob("*.sysml"):
        text = f.read_text(encoding="utf-8")
        m = re.search(rf"^[ \t]*requirement <'{re.escape(context.element)}'>", text, re.MULTILINE)
        if m:
            end = m.start() + arch.block(text, m.start()).__len__() + text[m.start():].index("{") + 2
            text = text[:m.start()] + text[end:].lstrip("\n")
        text = re.sub(rf"^.*\b{re.escape(context.name)}\b.*;\n", "", text, flags=re.MULTILINE)
        f.write_text(text, encoding="utf-8")
    context.world.commit("delete element")
    assert context.element not in core.model_ids(context.world.ws), "element still in the model"


@then('the ID "{element}" cannot be registered again')
def cannot_reregister(context, element):
    reason = ids.check_new_id(element, context.world.ws)
    assert reason and "never reused" in reason, reason


@when("I export the views")
def export_views(context):
    context.export_dir = context.world.dir / "export"
    context.export_dir.mkdir()
    for slug, _title, _desc, src in arch.build_diagrams():
        (context.export_dir / f"{slug}.mmd").write_text(src + "\n", encoding="utf-8")


@then("the export contains Mermaid text files")
def export_has_mermaid(context):
    files = sorted(context.export_dir.glob("*.mmd"))
    assert files, "no .mmd files exported"
    assert all(f.read_text(encoding="utf-8").strip() for f in files), "empty diagram"


@then("each file can be rendered without error")
def export_renders(context):
    assert shutil.which("node"), "node is required to check the Mermaid files"
    assert (CODE_ROOT / "tools/node/node_modules").is_dir(), "tools/node is not installed (./setup.sh --install)"
    for f in sorted(context.export_dir.glob("*.mmd")):
        r = subprocess.run(["node", "tools/node/check_mermaid.mjs", str(f)], cwd=CODE_ROOT, capture_output=True, text=True, check=False)
        assert r.returncode == 0, f"{f.name}: {r.stdout}{r.stderr}"


SYSON_URL = "http://localhost:8080/api/rest/projects"
SYSON_SKIP = "manual: needs SysON UI import"


@when("I load the model files into the graphical review tool")
def load_into_syson(context):
    # SysON has no import API; import is a UI action, so this scenario can only be verified manually.
    r = subprocess.run(["curl", "-sf", "--max-time", "5", SYSON_URL], capture_output=True, text=True, check=False)
    context.syson_reachable = r.returncode == 0
    context.scenario.skip(SYSON_SKIP)


@then("the model elements are displayed")
def elements_displayed(_):
    raise AssertionError("SysON import must be verified manually")


@when("one requirement text changes")
def requirement_changes(context):
    context.changed = context.world.edit_element("SR-004", "a changed requirement text")


@then("the textual diff shows exactly that change")
def diff_exact(context):
    w = context.world
    assert w.git("diff", "--name-only").stdout.split() == [str(context.changed.relative_to(w.root))]
    diff = w.git("diff", "-U0").stdout
    changed = [l for l in diff.splitlines() if l[:1] in "+-" and not l.startswith(("+++", "---"))]
    assert any("a changed requirement text" in l for l in changed if l.startswith("+")), diff
    assert len(diff.split("\n@@")) - 1 == 1, "more than one hunk changed"


async def _list_in_process(server):
    from mcp import Client
    async with Client(server) as c:
        return [t.name for t in (await c.list_tools()).tools], [p.name for p in (await c.list_prompts()).prompts]


async def _list_stdio(script, root):
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    params = StdioServerParameters(command=sys.executable, args=[str(CODE_ROOT / "tools" / script)],
                                   env={**os.environ, "SPECFLOW_ROOT": str(root)})
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as s:
            await s.initialize()
            return [t.name for t in (await s.list_tools()).tools], [p.name for p in (await s.list_prompts()).prompts]


@when("a compliant MCP client connects to the {server} server")
def connect_mcp(context, server):
    import importlib
    module = importlib.import_module(f"mcp_{server}")
    context.mcp_script = f"mcp_{server}.py"
    context.mcp_result = asyncio.run(_list_in_process(module.mcp))


@then("the client can list its tools and prompts")
def client_lists(context):
    tools, prompts = context.mcp_result
    assert tools and prompts, context.mcp_result
    stdio_tools, stdio_prompts = asyncio.run(_list_stdio(context.mcp_script, context.world.root))
    assert sorted(stdio_tools) == sorted(tools) and sorted(stdio_prompts) == sorted(prompts)
