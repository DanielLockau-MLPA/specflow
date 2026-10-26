Feature: Approvals and gates
  Gates G1 to G4 open only on signed approvals from every required human role.

  Background:
    Given a project workspace

  @SR-008 @DR-012
  Scenario: An approval is a signed tag carrying the mandatory information
    When the registered human "alice" with role "systems-engineer" approves gate "G2" with rationale "reviewed"
    Then the signed tag "approval/G2/systems-engineer" exists
    And the tag signature identifies the approver and the date
    And the tag message holds the rationale
    And the approval reports the content hash of the gate scope

  @SR-008 @DR-012
  Scenario: A newer approval supersedes an older one and the older one stays in history
    Given "alice" approved gate "G2" as "systems-engineer"
    When "alice" approves gate "G2" as "systems-engineer" again
    Then the newer approval counts
    And the older approval remains in the history

  @SR-008 @DR-014
  Scenario Outline: A gate opens only when every required role has approved
    Given the gate "<gate>" requires the roles "<required>"
    And the roles "<approved>" hold valid approvals for the current content
    And the trace rules report no unwaived gap
    When I evaluate gate "<gate>"
    Then the gate <result>

    Examples:
      | gate | required                                                      | approved                                                      | result       |
      | G1   | requirements-owner, systems-engineer                          | requirements-owner, systems-engineer                          | opens        |
      | G1   | requirements-owner, systems-engineer                          | requirements-owner                                            | stays closed |
      | G2   | systems-engineer, reviewer, information-security              | systems-engineer, reviewer                                    | stays closed |
      | G4   | implementation-team, quality-management, information-security | implementation-team, quality-management, information-security | opens        |

  @SR-008 @DR-014
  Scenario: A gate does not open while a trace gap is unwaived
    Given all required roles hold valid approvals for gate "G3"
    And the trace rules report an unwaived gap
    When I evaluate gate "G3"
    Then the gate stays closed
    And the gap is listed

  @SR-008 @DR-014
  Scenario: The implementation gate needs passing scenarios
    Given all required roles hold valid approvals for gate "G4"
    And a scenario of the specification fails
    When I evaluate gate "G4"
    Then the gate stays closed

  @SR-008 @DR-014
  Scenario: An approval for outdated content does not count
    Given the required roles approved an earlier version of the model
    And the model content has changed since
    When I evaluate gate "G2"
    Then the gate stays closed
    And the approvals are reported as stale

  @SR-031 @DR-013
  Scenario Outline: Only registered human keys with the role can approve
    When the signer "<signer>" tries to approve gate "G2" as "<role>"
    Then the approval is <outcome>

    Examples:
      | signer  | role             | outcome  |
      | alice   | systems-engineer | accepted |
      | agent-1 | systems-engineer | rejected |
      | mallory | unregistered     | rejected |

  @SR-031 @DR-013
  Scenario: A signer without the role mapping is rejected
    Given "alice" is registered but not mapped to the role "reviewer"
    When "alice" tries to approve gate "G2" as "reviewer"
    Then the approval is rejected

  @SR-031 @DR-013
  Scenario: Single-person approval opens a gate only when explicitly allowed
    Given one person signed the approvals for all roles of gate "G2"
    When I evaluate gate "G2" with single-person approval not allowed
    Then the gate stays closed
    When I evaluate gate "G2" with single-person approval allowed in the gate configuration
    Then the gate opens
    And the status reports single-person approval

  @SR-012 @DR-016
  Scenario: Changing approved content makes the approvals of that gate stale
    Given gate "G2" is open
    When the content of "SR-004" changes
    Then the approvals of gate "G2" are reported as stale
    And all approval tags are retained

  @SR-012 @DR-016
  Scenario: An unrelated gate stays open
    Given gates "G2" and "G3" are open
    When the content of "SR-004" changes
    Then gate "G3" remains open
