"""Helpers shared by the trace, coverage and run steps (no step definitions): model/spec mutations in a world."""
import re

import arch

SYNTH_STEPS = '''from behave import given


@given("a passing step")
def passing(context):
    pass


@given("a failing step")
def failing(context):
    assert False, "deliberate failure"
'''


def rewrite(files, fn):
    """Apply fn(text) -> text to the files; return how many changed."""
    changed = 0
    for f in files:
        text = f.read_text(encoding="utf-8")
        new = fn(text)
        if new != text:
            f.write_text(new, encoding="utf-8")
            changed += 1
    return changed


def model_files(world):
    return sorted((world.root / "model").glob("*.sysml"))


def feature_files(world):
    return sorted((world.root / "specs/features").glob("*.feature"))


def drop_dependencies(world, label_regex):
    """Remove every `dependency '<label>' ...;` statement whose label matches."""
    pattern = re.compile(rf"^[ \t]*dependency '{label_regex}'[^;]*;\n", re.M)
    return rewrite(model_files(world), lambda t: pattern.sub("", t))


def drop_satisfy(world, element):
    name = arch.ids_and_names(arch.read_model(world.root))[0]
    by_id = {i: n for n, i in name.items()}
    pattern = re.compile(rf"^[ \t]*satisfy {by_id[element]} by [\w.]+;\n", re.M)
    return rewrite(model_files(world), lambda t: pattern.sub("", t))


def drop_scenario_tag(world, tag):
    return rewrite(feature_files(world), lambda t: re.sub(rf"(?<=\s)@{re.escape(tag)}\b[ \t]*", "", t))


def tag_first_scenario(world, tag):
    def add(text):
        return re.sub(r"^([ \t]*@\S.*)$", rf"\1 @{tag}", text, count=1, flags=re.M)
    return rewrite(feature_files(world)[:1], add)


def untag_first_scenario(world):
    """Blank the first tag line that directly precedes a scenario; return the scenario location file:line."""
    for f in feature_files(world):
        lines = f.read_text(encoding="utf-8").split("\n")
        for n, line in enumerate(lines):
            if line.strip().startswith("@") and lines[n + 1].strip().startswith("Scenario"):
                lines[n] = ""
                f.write_text("\n".join(lines), encoding="utf-8")
                return f"{f.name}:{n + 2}"
    raise AssertionError("no tagged scenario found")


def synthetic_spec(world, scenarios):
    """Replace the world's features with tiny ones; scenarios is a list of (tags, step) with step passing or failing."""
    for f in feature_files(world):
        f.unlink()
    body = "Feature: Synthetic\n"
    for n, (tags, step) in enumerate(scenarios, 1):
        body += f"\n  {tags}\n  Scenario: Synthetic {n}\n    Given a {step} step\n"
    (world.root / "specs/features/x.feature").write_text(body, encoding="utf-8")
    steps = world.root / "specs/steps"
    steps.mkdir(parents=True, exist_ok=True)
    (steps / "x.py").write_text(SYNTH_STEPS, encoding="utf-8")
    world.commit("synthetic specification")
