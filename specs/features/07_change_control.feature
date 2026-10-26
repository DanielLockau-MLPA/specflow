Feature: Change control, impact and audit evidence
  Changes to approved items are attributable and analysed; evidence is retained per gate.

  Background:
    Given a project workspace

  @SR-010 @DR-017
  Scenario Outline: Impact analysis lists upstream and downstream elements
    Given a model and a specification with complete trace links
    When I analyse the impact of a change to "<element>"
    Then the impact lists the upstream elements "<upstream>"
    And the impact lists the downstream elements and scenarios "<downstream>"

    Examples:
      | element | upstream | downstream            |
      | SR-004  | N-001    | DR-002, its scenarios |
      | DR-002  | SR-004   | its scenarios         |

  @SR-010 @SR-012
  Scenario: A change to approved content requires re-approval
    Given gate "G2" is open
    When the content of "SR-004" changes
    Then gate "G2" requires re-approval before any gate that relies on it opens
    And the impact names the affected elements and scenarios

  @SR-030
  Scenario: A change to approved content is attributable
    Given gate "G2" is open
    When "alice" changes "SR-004" on a proposal branch with the reason "clarify scope" and "bob" approves it
    Then the change record names who, when, why and the approver
    And the change record is retained in the history

  @SR-030
  Scenario: A change without reason or approver is incomplete
    Given gate "G2" is open
    When "alice" changes "SR-004" without a reason
    Then the change is reported as an incomplete change record

  @SR-032 @DR-020
  Scenario: Evidence per gate links requirements to test results
    Given gate "G3" is open after a passing specification run
    When I inspect the evidence bundle of "G3"
    Then the bundle contains the scope content hashes, the approvals, the waivers, the spec results, the trace report and the tool versions
    And each requirement is linked to its test results

  @SR-032 @DR-031
  Scenario Outline: Audit queries work without the agent
    Given gate "G3" with approvals, waivers, changes and test evidence
    And no MCP client
    When I query the <subject> of gate "G3"
    Then the result lists the matching records

    Examples:
      | subject          |
      | approvals        |
      | waivers          |
      | changes          |
      | test evidence    |
      | integrity status |
