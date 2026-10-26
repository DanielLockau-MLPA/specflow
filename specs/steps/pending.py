"""G3 binding: the system under specification is not built yet.

Every step is accepted so the specification is syntactically executable
(`behave --dry-run`), and a real run reports the scenarios as skipped with the
reason below. Replace this module with real step modules at G4; the phrases to
implement are listed in docs/step_vocabulary.md.
"""
from behave import given, then, when

PENDING_REASON = "pending: system under specification not built (G4 binds real steps)"


def _pending(context, text):
    context.scenario.skip(PENDING_REASON)


@given("{text}")
def given_pending(context, text):
    _pending(context, text)


@when("{text}")
def when_pending(context, text):
    _pending(context, text)


@then("{text}")
def then_pending(context, text):
    _pending(context, text)
