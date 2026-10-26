Feature: Recorded Q&A and decision log
  Humans and the agent clarify intent in a recorded Q&A before any draft is produced.
  Outcomes are kept in an append-only decision log linked to model element IDs.

  Background:
    Given a project workspace

  @SR-001 @DR-022
  Scenario Outline: Q&A prompts instruct the agent to ask first
    When I fetch the workflow prompt "<prompt>"
    Then the prompt instructs the agent to ask clarifying questions before drafting
    And the prompt instructs the agent to record every outcome in the decision log
    And the prompt instructs the agent never to claim approval

    Examples:
      | prompt   |
      | model-qa |
      | spec-qa  |

  @SR-001
  Scenario Outline: Drafting is refused without a recorded Q&A for the stage
    Given no Q&A is recorded for stage "<stage>"
    When the agent requests a "<stage>" draft
    Then the request is refused with the reason "Q&A required"

    Examples:
      | stage |
      | model |
      | spec  |

  @SR-007 @DR-021
  Scenario: A decision entry carries all mandatory fields
    When a decision is recorded for stage "model" about "SR-004" with participants "alice, agent"
    Then the decision log for stage "model" gains one entry
    And the entry has a unique ID, a date, participants, question, decision, rationale and affected element IDs

  @SR-007 @DR-021
  Scenario: The decision log is append-only
    Given a decision log entry "DL-001" exists for stage "model"
    When I try to modify or delete the entry "DL-001"
    Then the change is rejected
    And the entry "DL-001" is unchanged

  @SR-007 @SR-022
  Scenario: A decision cannot reference an unknown element
    When a decision is recorded for stage "model" about "SR-999" with participants "alice"
    Then the request is refused with the reason "unknown element ID"
