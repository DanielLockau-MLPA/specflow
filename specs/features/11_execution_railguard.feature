# SPDX-FileCopyrightText: (C) 2026 ML!PA Consulting GmbH
# SPDX-License-Identifier: MIT

Feature: Execution railguard
  The implementation contains nothing that no scenario executes. Functions that stay unexecuted need a reviewed reason.

  @SR-018 @DR-037
  Scenario: A function that no scenario executes is reported
    Given an implementation with the functions "tools/a.py:f" and "tools/a.py:g"
    And an execution trace that entered only "tools/a.py:f"
    When the railguard check is evaluated
    Then the check fails
    And the report names "tools/a.py:g" as never executed

  @SR-018 @DR-037
  Scenario: An allowlisted function with a reason does not fail the check
    Given an implementation with the functions "tools/a.py:f" and "tools/a.py:g"
    And an execution trace that entered only "tools/a.py:f"
    And an allowlist entry for "tools/a.py:g" with the reason "operator tool, verified manually"
    When the railguard check is evaluated
    Then the check passes
    And the report lists "tools/a.py:g" as allowlisted

  @SR-018 @DR-037
  Scenario: An allowlist entry without a reason is refused
    Given an implementation with the functions "tools/a.py:f" and "tools/a.py:g"
    And an execution trace that entered only "tools/a.py:f"
    And an allowlist entry for "tools/a.py:g" without a reason
    When the railguard check is evaluated
    Then the check fails
    And the report names "tools/a.py:g" as never executed
    And the report contains a problem about an entry without a reason

  @SR-018 @DR-036
  Scenario: Functions entered in a subprocess are recorded
    Given a trace directory for a spec run
    When a subprocess of the spec run enters a function of the implementation
    Then the merged execution trace contains that function

  @SR-018 @DR-036 @DR-037
  Scenario: A run without an execution trace is not evidence
    Given an implementation with the functions "tools/a.py:f" and "tools/a.py:g"
    And no execution trace was recorded
    When the railguard check is evaluated
    Then the check fails
    And the report contains a problem about a missing execution trace
