Feature: Open formats, IDs and views
  Artifacts are open text, IDs are stable and unique, and views are exportable.

  Background:
    Given a project workspace

  @SR-020 @DR-029
  Scenario: Persistent artifacts use only open text formats
    When I list all persistent artifacts of the project
    Then every artifact has one of the extensions ".sysml", ".feature", ".yaml", ".json" or ".md", except public key files under "approvals/keys"

  @SR-020
  Scenario: The model can be read without the toolchain
    Given a valid model
    When the files are opened with a plain text editor
    Then the requirements and their IDs are readable

  @SR-022 @DR-028
  Scenario Outline: IDs follow the scheme and are unique
    When the ID "<id>" is registered for a new element
    Then the registration is <outcome>

    Examples:
      | id      | outcome  |
      | SR-100  | accepted |
      | SR-001  | rejected |
      | sr_1    | rejected |
      | XX-001  | rejected |

  @SR-022 @DR-028
  Scenario: IDs survive renaming and are never reused
    Given the element "SR-004" with the name "ValidateModel"
    When the element is renamed to "CheckModel"
    Then the element is still found by the ID "SR-004"
    When the element is deleted
    Then the ID "SR-004" cannot be registered again

  @SR-009 @DR-027
  Scenario: Diagrams are exported as Mermaid text
    Given a valid model
    When I export the views
    Then the export contains Mermaid text files
    And each file can be rendered without error

  @SR-009 @DR-027 @manual
  Scenario: The model is loadable in a graphical modeling tool
    Given a valid model
    When I load the model files into the graphical review tool
    Then the model elements are displayed

  @SR-009
  Scenario: Model changes are diff-able
    Given a valid model
    When one requirement text changes
    Then the textual diff shows exactly that change

  @SR-011
  Scenario Outline: Any compliant MCP client can use the servers
    When a compliant MCP client connects to the <server> server
    Then the client can list its tools and prompts

    Examples:
      | server |
      | model  |
      | spec   |
