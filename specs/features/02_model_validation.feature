# SPDX-FileCopyrightText: (C) 2026 ML!PA Consulting GmbH
# SPDX-License-Identifier: MIT

Feature: Model validation
  The model is validated by a replaceable parser backend; findings are located precisely.

  Background:
    Given a project workspace

  @SR-004 @DR-002
  Scenario Outline: Findings carry location, element and severity
    Given a model file containing <defect>
    When I validate the model
    Then the report contains a finding with severity "<severity>"
    And the finding names the file, the line and the element ID

    Examples:
      | defect                      | severity |
      | a syntax error in SR-004    | error    |
      | a requirement without a doc | warning  |

  @SR-004
  Scenario: A valid model validates without errors
    Given a valid model
    When I validate the model
    Then the report contains no findings with severity "error"

  @DR-002
  Scenario: The parser backend can be replaced
    Given a configured parser backend "alternative"
    When I validate the model
    Then the report has the same structure as for the default backend

  @DR-001 @SR-011
  Scenario: The model server exposes the documented tools
    When an MCP client lists the tools of the model server
    Then the tools include "list", "read", "search", "validate", "trace", "render" and "propose_edit"

  @DR-001
  Scenario: Reading and searching elements by ID
    Given a valid model
    When an MCP client reads the element "SR-004"
    Then the result contains the element text and its kind
    When an MCP client searches for "validate"
    Then the result lists "SR-004"
