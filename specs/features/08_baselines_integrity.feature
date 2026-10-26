Feature: Baselines and integrity
  Baselines are signed, tamper-evident and protected from the agent.

  Background:
    Given a project workspace

  @SR-041 @DR-018
  Scenario: A baseline tag is created only after gate evaluation succeeds
    Given gate "G2" has unmet conditions
    When I create the baseline for gate "G2"
    Then no baseline tag is created

  @SR-041 @DR-018
  Scenario: A baseline is a signed tag referencing its approvals
    Given gate "G2" is open
    When I create the baseline for gate "G2"
    Then a signed tag is created
    And the tag references the approval records it relies on

  @SR-041 @DR-019
  Scenario: A baseline records content hashes of model and specification
    Given gate "G3" is open
    When I create the baseline for gate "G3"
    Then the baseline records the content hashes of the model and the specification

  @SR-041 @DR-019
  Scenario Outline: Drift from the baseline is detected
    Given an approved baseline
    When the <artifact> is modified without a new baseline
    And I verify the baseline
    Then the verification reports a difference for the <artifact>

    Examples:
      | artifact      |
      | model         |
      | specification |

  @SR-041
  Scenario: A manipulated tag is detected
    Given an approved baseline
    When the baseline tag is replaced by an unsigned tag
    And I verify the baseline
    Then the verification reports an invalid signature

  @SR-040 @DR-026
  Scenario: The agent identity has no access to baseline refs
    Given the agent identity
    When it tries to push to a baseline ref
    Then the push is rejected by the repository host or hook
    And the rejection does not depend on the checks of the servers

  @SR-040 @DR-026
  Scenario: Baselines change only through the approval process
    Given an approved baseline
    When a non-agent identity pushes directly to a baseline ref without a gate evaluation
    Then the push is rejected
