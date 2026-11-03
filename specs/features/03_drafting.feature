Feature: Agent drafting of model and specification
  The agent drafts only from approved input and only as proposals on a proposal branch.

  Background:
    Given a project workspace

  @SR-002
  Scenario: Model drafting requires an approved requirement baseline
    Given no approved requirement baseline exists
    When the agent requests a "model" draft
    Then the request is refused with the reason "no approved baseline"

  @SR-002 @DR-003
  Scenario: A model draft is delivered as a proposal
    Given an approved requirement baseline
    And a recorded Q&A for stage "model"
    When the agent proposes a model edit
    Then the change lands on a branch matching "proposal/*"
    And the proposed content has the status "DRAFT"

  @SR-003
  Scenario: Specification drafting requires an approved model
    Given no approved model baseline exists
    When the agent requests a "spec" draft
    Then the request is refused with the reason "no approved baseline"

  @SR-003 @DR-005 @DR-006
  Scenario: Drafted scenarios reference the model elements they verify
    Given an approved model baseline
    And a recorded Q&A for stage "spec"
    When the agent drafts scenarios for the requirement "SR-004"
    Then each drafted scenario carries the tag "@SR-004"
    And no drafted scenario carries a tag naming a non-existing element

  @DR-006
  Scenario: A scenario without a valid ID tag is invalid
    Given a specification containing a scenario without any ID tag
    When I run the spec check
    Then the check reports the scenario as invalid

  @DR-005
  Scenario: The spec server exposes the documented tools
    When an MCP client lists the tools of the spec server
    Then the tools include "list", "draft", "propose_edit", "run" and "coverage"

  @DR-003 @SR-040
  Scenario Outline: Proposals are only accepted on proposal branches
    When the agent writes a proposal to "<ref>"
    Then the write is <outcome>

    Examples:
      | ref                | outcome  |
      | proposal/new-links | accepted |
      | main               | rejected |
      | baseline/G2        | rejected |

  @DR-003 @SR-040
  Scenario: Files of an approved baseline cannot be changed by a proposal
    Given an approved model baseline
    When the agent proposes a change to a file of that baseline
    Then the write is rejected

  @DR-003 @DR-035 @SR-040
  Scenario: An operator-unlocked proposal branch accepts a change to a baseline file
    Given an approved model baseline
    And the operator unlocked the proposal branch "proposal/model-draft"
    When the agent proposes a change to a file of that baseline
    Then the write is accepted
    And the commit on the proposal branch carries the trailer "Unlocked-Baseline"

  @DR-003 @DR-035 @SR-040
  Scenario: An unlock of another proposal branch does not open this one
    Given an approved model baseline
    And the operator unlocked the proposal branch "proposal/other-draft"
    When the agent proposes a change to a file of that baseline
    Then the write is rejected
