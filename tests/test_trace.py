import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
from trace import check, load_model, load_scenarios  # noqa: E402

INFO = {i: ("x", "") for i in ["N-001", "N-002", "UC-01", "SR-001", "DR-001"]}
LINKS = [("UC-01", "covers", "N-001"), ("UC-01", "exercises", "SR-001"),
         ("SR-001", "derives", "N-001"), ("DR-001", "derives", "SR-001")]


def rules(stage, links=LINKS, allocated=frozenset({"DR-001"}), scenarios=()):
    return {(v["rule"], v["element"]) for v in check(stage, INFO, links, allocated, list(scenarios))}


def test_uncovered_need_is_reported():
    assert ("need-covered", "N-002") in rules("needs")


def test_model_orphans_are_reported():
    assert rules("model", links=[], allocated=frozenset()) >= {
        ("usecase-exercises", "UC-01"), ("l1-derives-need", "SR-001"),
        ("l2-derives-l1", "DR-001"), ("l2-allocated", "DR-001")}


def test_spec_gaps_are_reported():
    sc = [{"file": "f", "line": 1, "name": "a", "tags": ["SR-999"]},
          {"file": "f", "line": 2, "name": "b", "tags": ["wip"]}]
    got = rules("spec", scenarios=sc)
    assert ("tag-valid", "SR-999") in got
    assert ("scenario-tagged", "f:2") in got
    assert ("requirement-verified", "SR-001") in got and ("requirement-verified", "DR-001") in got


def test_project_model_and_specs_are_trace_complete():
    info, links, allocated = load_model()
    scenarios = load_scenarios()
    for stage in ("needs", "model", "spec"):
        assert check(stage, info, links, allocated, scenarios) == []
