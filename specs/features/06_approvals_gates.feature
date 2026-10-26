Feature: Approvals and gates
  Gates G1 to G4 open only on recorded, signed approvals from every required human role.

  Background:
    Given a project workspace

  @SR-008 @DR-012
  Scenario: An approval record contains all mandatory fields
    When the human "alice" with role "systems-engineer" approves the elements "SR-001, SR-002" with rationale "reviewed"
    Then an approval record is stored in the repository
    And the record has approver, role, decision, element IDs, content hash, rationale and date
    And the record is signed by the approver

  @SR-008 @DR-014
  Scenario Outline: A gate opens only when every required role has approved
    Given the gate "<gate>" requires the roles "<required>"
    And the roles "<approved>" hold valid approvals for the current content
    And the trace rules report no unwaived gap
    When I evaluate gate "<gate>"
    Then the gate <result>

    Examples:
      | gate | required                                | approved                  | result       |
      | G1   | requirements-owner, systems-engineer    | requirements-owner, systems-engineer | opens |
      | G1   | requirements-owner, systems-engineer    | requirements-owner        | stays closed |
      | G2   | systems-engineer, reviewer, security    | systems-engineer, reviewer | stays closed |
      | G4   | implementation, quality                 | implementation, quality   | opens        |

  @SR-008 @DR-014
  Scenario: An approval for outdated content does not count
    Given the roles "systems-engineer, reviewer, security" approved an earlier version of the model
    And the model content has changed since
    When I evaluate gate "G2"
    Then the gate stays closed

  @SR-031 @DR-013
  Scenario Outline: Only eligible human identities can approve
    When the identity "<identity>" of kind "<kind>" with role "<role>" tries to approve "SR-001"
    Then the approval is <outcome>

    Examples:
      | identity | kind  | role             | outcome  |
      | alice    | human | systems-engineer | accepted |
      | agent-1  | agent | systems-engineer | rejected |
      | mallory  | human | unregistered     | rejected |

  @SR-031 @DR-013
  Scenario: The author cannot be the only approver
    Given "alice" authored a change to "SR-001"
    When "alice" is the only approver of that change
    Then the approval does not satisfy the gate requirement

  @SR-012 @DR-016
  Scenario: Changing an approved element invalidates dependent approvals
    Given "SR-004" and its dependent "DR-002" are approved
    When the content of "SR-004" changes
    Then the approvals of "SR-004" are marked invalidated
    And the approvals of "DR-002" are marked invalidated
    And the original approval records are retained

  @SR-012 @DR-016
  Scenario: An unrelated approval stays valid
    Given "SR-004" and the unrelated element "SR-040" are approved
    When the content of "SR-004" changes
    Then the approvals of "SR-040" remain valid
