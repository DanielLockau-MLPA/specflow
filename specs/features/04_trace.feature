# SPDX-FileCopyrightText: (C) 2026 ML!PA Consulting GmbH
# SPDX-License-Identifier: MIT

Feature: Traceability checks and queries
  Trace completeness is checked per stage and gaps keep gates closed unless waived by a human.

  Background:
    Given a project workspace

  @SR-013 @DR-009
  Scenario Outline: Model trace rules report orphans and gaps
    Given a model in which <defect>
    When I run the trace check for stage "model"
    Then the report contains a violation of rule "<rule>" for the element "<element>"

    Examples:
      | defect                                         | rule                   | element |
      | use case UC-01 exercises no requirement        | usecase-exercises      | UC-01   |
      | requirement SR-001 derives from no need        | l1-derives-need        | SR-001  |
      | requirement DR-001 derives from no L1 requirement | l2-derives-l1       | DR-001  |
      | requirement DR-001 is allocated to no element  | l2-allocated           | DR-001  |

  @SR-013 @DR-009
  Scenario: A need without a use case is reported at the needs stage
    Given a model in which need N-001 is covered by no use case
    When I run the trace check for stage "needs"
    Then the report contains a violation of rule "need-covered" for the element "N-001"

  @SR-017 @DR-033
  Scenario Outline: Source rules report needs without sources and sources without stakeholders
    Given a model in which <defect>
    When I run the trace check for stage "needs"
    Then the report contains a violation of rule "<rule>" for the element "<element>"

    Examples:
      | defect                                 | rule               | element |
      | need N-003 cites no source             | need-sourced       | N-003   |
      | source SRC-002 names no stakeholder    | source-stakeholder | SRC-002 |
      | source SRC-004 is cited by no need     | source-cited       | SRC-004 |

  @SR-017 @DR-033
  Scenario Outline: Use cases and requirements must reach a source through their trace chain
    Given a model in which <defect>
    When I run the trace check for stage "model"
    Then the report contains a violation of rule "source-traceable" for the element "<element>"

    Examples:
      | defect                                         | element |
      | use case UC-03 covers no need                  | UC-03   |
      | requirement SR-001 derives from no need        | SR-001  |
      | requirement DR-001 derives from no L1 requirement | DR-001 |

  @SR-017 @DR-033
  Scenario: A complete set of needs and sources has no violations
    Given a model with complete trace links
    When I run the trace check for stage "needs"
    Then the report contains no violations

  @SR-013 @DR-009
  Scenario: A complete model has no trace violations
    Given a model with complete trace links
    When I run the trace check for stage "model"
    Then the report contains no violations

  @SR-014 @DR-009
  Scenario Outline: Spec trace rules report unverified requirements and bad references
    Given a specification in which <defect>
    When I run the trace check for stage "spec"
    Then the report contains a violation of rule "<rule>" for the element "<element>"

    Examples:
      | defect                                   | rule               | element  |
      | requirement SR-001 has no scenario       | requirement-verified | SR-001 |
      | a scenario is tagged with unknown @SR-999 | tag-valid          | SR-999   |
      | a scenario has no ID tag                 | scenario-tagged    | the scenario |

  @SR-015 @DR-014
  Scenario Outline: Trace gaps keep the gate closed
    Given a trace report with an unwaived gap
    And all required roles have approved
    When I evaluate gate "<gate>"
    Then the gate stays closed
    And the reason lists the gap

    Examples:
      | gate |
      | G2   |
      | G3   |

  @SR-015 @DR-015
  Scenario: A waiver lets the gate open and stays visible
    Given a trace report with a gap waived by a signed waiver with approver, rationale and expiry
    And all required roles have approved
    When I evaluate gate "G2"
    Then the gate opens
    And every report lists the waiver

  @SR-015 @DR-015
  Scenario Outline: Invalid waivers are not accepted
    Given a trace report with a gap and a waiver <problem>
    When I evaluate gate "G2"
    Then the gate stays closed

    Examples:
      | problem                |
      | without a rationale    |
      | whose expiry has passed |
      | signed by the agent    |

  @SR-017 @DR-034
  Scenario: Sources and stakeholders are declared as identified model elements
    Given a valid model
    When I list the requirement sources of the model
    Then each source has a kind, a reference and a stakeholder
    And each stakeholder has an ID

  @SR-016 @DR-008
  Scenario Outline: Trace queries work in both directions
    Given a model and a specification with complete trace links
    When I query the trace from "<from>" to "<to>"
    Then the result lists the connected elements

    Examples:
      | from  | to       |
      | N-001 | scenario |
      | scenario | N-001 |
      | SR-004 | DR-002  |
      | DR-002 | SR-004  |
      | DR-002 | SRC     |
      | SRC-002 | STK    |
      | STK-006 | N-008  |

  @SR-016 @DR-010
  Scenario: A reference to a removed element is reported as dangling
    Given an approved link to element "SR-004"
    When the element "SR-004" is removed
    Then the trace check reports a dangling reference to "SR-004"

  @SR-016 @DR-010
  Scenario: A link whose target changed since approval is reported as stale
    Given an approved link to element "SR-004"
    When the content of "SR-004" changes
    Then the trace check reports a stale reference to "SR-004"

  @DR-008 @SR-021
  Scenario: The trace graph is deterministic
    Given a model and a specification with complete trace links
    When I build the trace graph twice
    Then both serialisations are byte-identical
