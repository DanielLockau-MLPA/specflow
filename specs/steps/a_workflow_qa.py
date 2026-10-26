"""Steps of 01_workflow_qa.feature; also the shared 'refused' and 'draft request' steps used by drafting."""
import re

from behave import given, then, when

import a_mcp
import specflow_core as core

PROMPT_SERVER = {"model-qa": "model", "spec-qa": "spec"}
STAGE_DRAFT = {"model": ("model", "request_model_draft", {}), "spec": ("spec", "draft_scenarios", {"requirement_id": "SR-004"})}
FIELDS = ("date", "type", "participants", "question", "decision", "rationale", "affected")


def log_file(context, stage):
    return context.world.root / f"decisions/{stage}.md"


def entries(context, stage):
    text = log_file(context, stage).read_text(encoding="utf-8") if log_file(context, stage).exists() else ""
    return {m.group(1): m.group(2) for m in re.finditer(r"^## (DL-\d+)\n(.*?)(?=^## |\Z)", text, re.M | re.S)}


@when('I fetch the workflow prompt "{prompt}"')
def fetch_prompt(context, prompt):
    context.prompt = a_mcp.prompt_text(PROMPT_SERVER[prompt], prompt).lower()


@then("the prompt instructs the agent to ask clarifying questions before drafting")
def prompt_asks_first(context):
    assert "ask questions first" in context.prompt and "do not draft anything until" in context.prompt


@then("the prompt instructs the agent to record every outcome in the decision log")
def prompt_records(context):
    assert "record each outcome with record_decision" in context.prompt


@then("the prompt instructs the agent never to claim approval")
def prompt_no_approval(context):
    assert "never claim or imply approval" in context.prompt


@given('no Q&A is recorded for stage "{stage}"')
def no_qa(context, stage):
    path = log_file(context, stage)
    if path.exists():
        path.unlink()
        context.world.commit("remove decision log")
    assert not core.qa_recorded(stage, context.world.ws)


@given('a recorded Q&A for stage "{stage}"')
def recorded_qa(context, stage):
    core.record_decision(stage, "qa", ["alice", "agent"], "Is the scope clear?", "Yes", "Agreed in Q&A", ["SR-004"],
                         context.world.ws)
    assert core.qa_recorded(stage, context.world.ws)


@when('the agent requests a "{stage}" draft')
def request_draft(context, stage):
    server, tool, args = STAGE_DRAFT[stage]
    context.refused, context.reply = a_mcp.call(server, tool, args)


@then('the request is refused with the reason "{reason}"')
def refused(context, reason):
    assert context.refused, f"request was not refused: {context.reply}"
    assert reason in context.reply, context.reply


@when('a decision is recorded for stage "{stage}" about "{element}" with participants "{participants}"')
def record(context, stage, element, participants):
    context.stage = stage
    context.before = set(entries(context, stage))
    try:
        context.new_id = core.record_decision(stage, "qa", [p.strip() for p in participants.split(",")],
                                              "Which scope applies?", "Scope as discussed", "Agreed with the team",
                                              [element], context.world.ws)
        context.refused, context.reply = False, ""
    except core.Rejected as e:
        context.refused, context.reply = True, str(e)


@then('the decision log for stage "{stage}" gains one entry')
def gains_one(context, stage):
    assert not context.refused, context.reply
    assert set(entries(context, stage)) - context.before == {context.new_id}


@then("the entry has a unique ID, a date, participants, question, decision, rationale and affected element IDs")
def entry_fields(context):
    all_ids = [i for s in core.STAGES for i in entries(context, s)]
    assert len(all_ids) == len(set(all_ids))
    body = entries(context, context.stage)[context.new_id]
    values = dict(re.findall(r"^- (\w+): (.*)$", body, re.M))
    assert all(values.get(f) for f in FIELDS), values
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", values["date"])
    assert values["participants"] == "alice, agent" and values["affected"] == "SR-004"


@given('a decision log entry "{entry}" exists for stage "{stage}"')
def entry_exists(context, entry, stage):
    context.entry_text = entries(context, stage)[entry]
    context.entry_stage = stage
    context.log_before = log_file(context, stage).read_text(encoding="utf-8")


@when('I try to modify or delete the entry "{entry}"')
def modify_or_delete(context, entry):
    old = context.log_before
    start = old.index(f"## {entry}\n")
    end = old.find("\n## ", start)
    rel = f"decisions/{context.entry_stage}.md"
    variants = (old.replace(context.entry_text, context.entry_text.replace("- decision:", "- decision: CHANGED ")),
                old[:start] + (old[end + 1:] if end >= 0 else ""))
    context.rejections = []
    for n, content in enumerate(variants):
        assert content != old
        try:
            core.propose_edit(rel, content, f"proposal/edit-log-{n}", "edit log", context.world.ws)
            context.rejections.append(None)
        except core.Rejected as e:
            context.rejections.append(str(e))


@then("the change is rejected")
def change_rejected(context):
    assert all(r and "append-only" in r for r in context.rejections), context.rejections


@then('the entry "{entry}" is unchanged')
def entry_unchanged(context, entry):
    assert log_file(context, context.entry_stage).read_text(encoding="utf-8") == context.log_before
    assert entries(context, context.entry_stage)[entry] == context.entry_text
    assert not context.world.git("branch", "--list", "proposal/*").stdout.strip()
