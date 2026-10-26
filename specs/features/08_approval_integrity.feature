Feature: Approval integrity
  Approvals and waivers are signed, tamper-evident and protected from the agent.

  Background:
    Given a project workspace

  @SR-041 @DR-018
  Scenario Outline: Invalid approval tags are reported
    Given gate "G2" is open
    When the approval tag "approval/G2/reviewer" is <manipulation>
    And I verify gate "G2"
    Then the verification reports an invalid approval for the role "reviewer"
    And the gate is not open

    Examples:
      | manipulation                             |
      | replaced by an unsigned tag              |
      | replaced by a tag of an unregistered key |

  @SR-041 @DR-018
  Scenario Outline: Waivers must be valid to count
    Given a trace gap that is waived by a signed waiver tag with <condition>
    When I evaluate the trace rules
    Then the waiver is ignored
    And the gap is reported

    Examples:
      | condition              |
      | no rationale           |
      | a past expiry date     |
      | an unregistered signer |

  @SR-041 @DR-018
  Scenario: A valid waiver is listed in every report
    Given a trace gap that is waived by a valid signed waiver tag
    When I generate the coverage report
    Then the waiver is listed with its rationale and expiry

  @SR-041 @DR-019
  Scenario Outline: Drift from the approved content is detected
    Given gate "<gate>" is open
    When a file of the gate scope is modified without a new approval
    And I verify gate "<gate>"
    Then the verification reports the differing files of the gate scope

    Examples:
      | gate |
      | G2   |
      | G3   |

  @SR-040 @DR-026
  Scenario: The agent identity has no access to approval refs
    Given the agent identity
    When it tries to push to an approval or waiver ref
    Then the push is rejected by the repository host or hook
    And the rejection does not depend on the checks of the servers

  @SR-040 @DR-018
  Scenario: No agent-facing tool creates, moves or deletes approval refs
    Given the agent-facing tools of the servers
    When I list them
    Then none of them creates, moves or deletes an approval or waiver ref
