Feature: Coverage, spec execution and CI use
  Coverage and results are produced headless, deterministically and in machine-readable form.

  Background:
    Given a project workspace

  @SR-005 @DR-011
  Scenario: The coverage report covers every level and lists gaps
    Given a model and a specification with one uncovered requirement "SR-001"
    When I produce the coverage report
    Then the report has a summary for each level need, use case, requirement, design element and scenario
    And the report has a summary for each gate
    And the report lists "SR-001" as a gap

  @SR-005 @DR-011
  Scenario Outline: The coverage report exists as JSON and Markdown
    Given a model and a specification with complete trace links
    When I produce the coverage report as "<format>"
    Then the report is written in stable order

    Examples:
      | format   |
      | json     |
      | markdown |

  @SR-006 @DR-007
  Scenario: Each scenario result carries its ID tags, status and duration
    Given a specification with scenarios tagged "@SR-004" and "@SR-005"
    When I run the specification headless
    Then the result contains one entry per scenario
    And each entry has the ID tags, a status and a duration

  @SR-006
  Scenario: A failing scenario is reported with its requirement IDs
    Given a specification with a failing scenario tagged "@SR-004"
    When I run the specification headless
    Then the failing scenario is reported with the requirement "SR-004"

  @SR-021 @DR-030
  Scenario Outline: CLI commands return non-zero exit codes on failure
    Given a workspace in which <failure>
    When I run the CLI command "<command>"
    Then the exit code is not zero

    Examples:
      | failure                        | command  |
      | the model has a syntax error   | validate |
      | the trace has a gap            | trace    |
      | a scenario fails               | run      |
      | a gate has unmet conditions    | gate     |

  @SR-021
  Scenario: Identical inputs give identical results
    Given a model and a specification with complete trace links
    When I run validation, the trace check and the coverage report twice
    Then the results of both runs are identical

  @SR-021 @DR-030
  Scenario: The commands need no agent and no network
    Given a model and a specification with complete trace links
    And no MCP client and no network access
    When I run validation, the trace check and the coverage report
    Then all commands complete successfully
