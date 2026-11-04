# SPDX-FileCopyrightText: (C) 2026 ML!PA Consulting GmbH
# SPDX-License-Identifier: MIT

"""Steps shared by several features. Phrases here must not be redefined in other step modules."""
from behave import given, then, when

import approvals
import gate as gatelib
from world import World  # noqa: F401  (ensures the world module is loaded for all step files)


@given("a project workspace")
def project_workspace(context):
    assert (context.world.root / "model").is_dir() and (context.world.root / "specs/features").is_dir()


@given("a valid model")
@given("a model with complete trace links")
@given("a model and a specification with complete trace links")
def complete_model(context):
    """The world starts as a copy of the project model and specification, which are trace complete."""
    report = context.world.cli("trace", "--json")
    assert report.returncode == 0, report.stdout + report.stderr


@given('gate "{gate}" is open')
def gate_is_open(context, gate):
    context.world.approve_all(gate)
    assert approvals.gate_status(gate, context.world.ws)["open"], approvals.gate_status(gate, context.world.ws)["problems"]


@given('gates "{a}" and "{b}" are open')
def gates_are_open(context, a, b):
    for g in (a, b):
        gate_is_open(context, g)


@when('the content of "{element}" changes')
def content_changes(context, element):
    context.world.edit_element(element, f"changed text of {element}")
    context.world.commit(f"change {element}")
    context.changed_element = element


@when('I evaluate gate "{gate}"')
def evaluate_gate(context, gate):
    context.gate = gate
    context.report = gatelib.evaluate(gate, context.world.ws)


@then("the gate {result}")
def gate_result(context, result):
    expected = {"opens": True, "stays closed": False, "is not open": False}[result]
    assert context.report["open"] is expected, context.report["problems"]
