package DesignRequirements {
    doc /* L2 design requirements. Each derives from L1 requirements and is allocated to a part in package Architecture. */
    private import SystemRequirements::*;

    requirement def DesignRequirement {
        attribute kind : SystemRequirements::Kind;
        attribute status : ScalarValues::String;
    }

    // Model MCP server
    requirement <'DR-001'> ModelMcpTools : DesignRequirement {
        doc /* The model MCP server shall expose tools to list, read, search and validate model elements, query traces, render views, and propose edits. */
        attribute :>> kind = Kind::functional;
    }
    requirement <'DR-002'> ValidationWithLocation : DesignRequirement {
        doc /* Validation shall delegate to a replaceable parser backend and return each finding with file, line, element ID and severity. */
        attribute :>> kind = Kind::functional;
    }
    requirement <'DR-003'> ProposeOnBranchOnly : DesignRequirement {
        doc /* Propose-edit tools shall write only to branches matching proposal/*, and shall refuse any write to a baseline ref or to a file of an approved baseline. */
        attribute :>> kind = Kind::security;
    }
    requirement <'DR-004'> AiAuthorshipMarking : DesignRequirement {
        doc /* Every commit created through an agent session shall carry an AI-authorship trailer and the session identity, and its content shall have status DRAFT. */
        attribute :>> kind = Kind::security;
    }

    // Spec MCP server and runner
    requirement <'DR-005'> SpecMcpTools : DesignRequirement {
        doc /* The spec MCP server shall expose tools to list specifications, draft scenarios from model elements, propose edits on proposal branches, run specs, and report coverage. */
        attribute :>> kind = Kind::functional;
    }
    requirement <'DR-006'> ScenarioIdTags : DesignRequirement {
        doc /* Every scenario shall carry one tag per verified model element ID in the form @<ID>, for example @SR-005; scenarios without a valid tag are invalid. */
        attribute :>> kind = Kind::functional;
    }
    requirement <'DR-007'> HeadlessSpecRun : DesignRequirement {
        doc /* The spec runner shall execute all scenarios headless and emit a machine-readable result per scenario with its ID tags, status and duration. */
        attribute :>> kind = Kind::functional;
    }

    // Trace service
    requirement <'DR-008'> TraceIndex : DesignRequirement {
        doc /* The trace service shall build a trace graph from model relations and spec tags, serialised deterministically (sorted, no timestamps) for identical input. */
        attribute :>> kind = Kind::quality;
    }
    requirement <'DR-009'> TraceRules : DesignRequirement {
        doc /* The trace service shall evaluate rule sets per stage: needs (every need covered by a use case), model (derivation and allocation completeness), spec (requirement verified, scenario tags valid), and report violations by rule and element ID. */
        attribute :>> kind = Kind::functional;
    }
    requirement <'DR-010'> StaleReferenceDetection : DesignRequirement {
        doc /* The trace service shall detect references to IDs that no longer exist or whose content hash changed since the link was approved. */
        attribute :>> kind = Kind::functional;
    }
    requirement <'DR-011'> CoverageReportFormat : DesignRequirement {
        doc /* Coverage reports shall be produced as JSON and Markdown with a stable ordering and a summary per level and per gate. */
        attribute :>> kind = Kind::functional;
    }

    // Approvals, gates, impact
    requirement <'DR-012'> ApprovalRecord : DesignRequirement {
        doc /* An approval shall be a signed git tag named approval/<gate>/<role>.<revision>, created by a registered human approver for the gate scope at one commit (HEAD by default; an approver may name an earlier commit only if the gate scope is identical at HEAD); the signature gives approver identity and date, the tag name gives role and gate, the tag message gives the rationale, and the content hash is computed from the scope at the tagged commit. A newer approval of the same role supersedes older ones, which stay in the history. The approvals of one gate revision are all on the same commit; an approval on a later commit starts a new revision that every role must sign again. */
        attribute :>> kind = Kind::normative;
    }
    requirement <'DR-013'> ApproverEligibility : DesignRequirement {
        doc /* The approval service shall accept an approval only if its signing key is registered in approvals/keys and mapped to the role in approvals/roles.json; agents hold no registered key. A gate whose approvals all come from one person shall open only if single-person approval is explicitly allowed in the gate configuration, and the status shall report it. */
        attribute :>> kind = Kind::normative;
    }
    requirement <'DR-014'> GateEvaluation : DesignRequirement {
        doc /* The gate evaluator shall derive the gate state and open a gate only if all required roles hold valid approvals on the same commit for the current scope content, the trace rules of the gate report no unwaived gap, no AI-authored change in scope is unreviewed, and for the implementation gate all scenarios pass. No separate gate-open record exists. */
        attribute :>> kind = Kind::functional;
    }
    requirement <'DR-015'> WaiverRecord : DesignRequirement {
        doc /* A waiver shall be a signed git tag named waiver/<rule>/<element> by a registered human approver, with the rationale and an expiry date in the tag message; it shall be listed in every report, and a waiver without rationale, with a past expiry or without a registered signer shall be ignored. */
        attribute :>> kind = Kind::normative;
    }
    requirement <'DR-016'> ApprovalInvalidation : DesignRequirement {
        doc /* When the content of a gate scope changes, the approval service shall report every approval of that gate as stale, leave approvals of gates with unchanged scope valid, and retain all approval tags. */
        attribute :>> kind = Kind::functional;
    }
    requirement <'DR-017'> ImpactAnalysis : DesignRequirement {
        doc /* The impact analyzer shall compute, from the trace graph, all upstream and downstream elements and scenarios affected by a changed element. */
        attribute :>> kind = Kind::functional;
    }

    // Baselines and evidence
    requirement <'DR-018'> TamperEvidentApprovals : DesignRequirement {
        doc /* Approval and waiver tags shall be tamper-evident: a tag that is unsigned, signed by an unregistered key or altered shall be reported as invalid, and no agent-facing tool shall create, move or delete approval or waiver refs. Protection of these refs on the git host is a deployment requirement. */
        attribute :>> kind = Kind::security;
    }
    requirement <'DR-019'> DriftDetection : DesignRequirement {
        doc /* Verification shall compute the scope content hash at each approval and report every file of the gate scope that differs from the current content. */
        attribute :>> kind = Kind::security;
    }
    requirement <'DR-020'> EvidenceBundle : DesignRequirement {
        doc /* Per gate, the system shall write an evidence bundle containing the scope content hashes, the approvals, the waivers, the spec results, the trace report and the tool versions, so that requirement-to-test evidence can be inspected later. */
        attribute :>> kind = Kind::normative;
    }
    requirement <'DR-021'> DecisionLogFormat : DesignRequirement {
        doc /* The decision log shall be an append-only text file per stage; each entry has a unique ID, date, participants, question, decision, rationale and affected element IDs. */
        attribute :>> kind = Kind::functional;
    }
    requirement <'DR-022'> WorkflowPrompts : DesignRequirement {
        doc /* The system shall provide MCP prompts for the Q&A and review phases that instruct the agent to ask questions first, record outcomes in the decision log, and never claim approval. */
        attribute :>> kind = Kind::functional;
    }

    // Security
    requirement <'DR-023'> PathContainment : DesignRequirement {
        doc /* Every file path received by a tool shall be resolved to a canonical path, symlinks resolved, and rejected if outside the workspace root or inside a protected directory. */
        attribute :>> kind = Kind::security;
    }
    requirement <'DR-024'> UntrustedContentHandling : DesignRequirement {
        doc /* Content from input documents shall be returned to the agent labelled as untrusted data, and all agent-facing MCP traffic shall pass through the input guard, which requests human confirmation (DR-032) for state-changing tool calls. */
        attribute :>> kind = Kind::security;
    }
    requirement <'DR-025'> ConfidentialityExclusions : DesignRequirement {
        doc /* A configurable exclusion list of paths and classification markers shall prevent matching content from being returned by any tool; exclusions shall be logged. */
        attribute :>> kind = Kind::security;
    }
    requirement <'DR-026'> RefProtectionOutsideAgent : DesignRequirement {
        doc /* The agent identity shall have no credentials for baseline refs; protection shall be enforced by git hooks or host branch protection in addition to the checks in the servers. */
        attribute :>> kind = Kind::security;
    }

    requirement <'DR-032'> HumanConfirmationChannel : DesignRequirement {
        doc /* Confirmation of a state-changing tool call shall be requested from the human through a channel outside the agent session (client confirmation dialog or terminal prompt); the agent shall receive only the decision, and a missing or negative answer shall abort the call. */
        attribute :>> kind = Kind::security;
    }
    requirement <'DR-033'> SourceTraceRules : DesignRequirement {
        doc /* The trace service shall evaluate the source rules need-sourced, source-stakeholder and source-cited in stage needs, and source-traceable in stage model, where a use case or requirement reaches a source if a covers, derives or cites chain leads to it; sources are cited at the highest possible level and inherited downwards. */
        attribute :>> kind = Kind::functional;
    }
    requirement <'DR-034'> SourceDeclaration : DesignRequirement {
        doc /* Requirement sources shall be declared as SysML items with the short name SRC-<number>, a kind (norm, communication or document) and a reference to the written source; stakeholders shall be declared as parts with the short name STK-<number>; needs link to sources with 'cites' and sources link to stakeholders with 'raisedBy' dependencies. */
        attribute :>> kind = Kind::functional;
    }

    // Quality and format
    requirement <'DR-027'> ViewExport : DesignRequirement {
        doc /* The system shall export diagrams as Mermaid text and provide model files loadable in SysON for graphical review. */
        attribute :>> kind = Kind::functional;
    }
    requirement <'DR-028'> StableIdScheme : DesignRequirement {
        doc /* IDs shall be declared as SysML short names, follow the pattern <PREFIX>-<number> with the prefixes N, SRC, STK, UC, SR and DR, be unique across the workspace, and never be reused after deletion. */
        attribute :>> kind = Kind::quality;
    }
    requirement <'DR-029'> OpenFormatsOnly : DesignRequirement {
        doc /* Persistent artifacts shall be limited to .sysml, .feature, JSON and Markdown files in the repository. */
        attribute :>> kind = Kind::quality;
    }
    requirement <'DR-030'> HeadlessCli : DesignRequirement {
        doc /* Validation, trace checks, spec runs and gate evaluation shall also be available as CLI commands returning non-zero exit codes on failure for CI use. */
        attribute :>> kind = Kind::quality;
    }
    requirement <'DR-031'> AuditQuery : DesignRequirement {
        doc /* The system shall provide a query for approvals, waivers, changes, test evidence and integrity status per baseline, usable without the agent. */
        attribute :>> kind = Kind::functional;
    }

    // Derivation L2 -> L1
    dependency 'DR-001 derives SR-011' from ModelMcpTools to AgentAccessViaMcp;
    dependency 'DR-001 derives SR-004' from ModelMcpTools to ValidateModel;
    dependency 'DR-002 derives SR-004' from ValidationWithLocation to ValidateModel;
    dependency 'DR-003 derives SR-040' from ProposeOnBranchOnly to NoAgentWriteToBaseline;
    dependency 'DR-003 derives SR-002' from ProposeOnBranchOnly to DraftModelFromBaseline;
    dependency 'DR-004 derives SR-045' from AiAuthorshipMarking to AiContributionMarked;
    dependency 'DR-005 derives SR-011' from SpecMcpTools to AgentAccessViaMcp;
    dependency 'DR-005 derives SR-003' from SpecMcpTools to DraftSpecFromModel;
    dependency 'DR-006 derives SR-003' from ScenarioIdTags to DraftSpecFromModel;
    dependency 'DR-006 derives SR-014' from ScenarioIdTags to SpecTraceCompleteness;
    dependency 'DR-007 derives SR-006' from HeadlessSpecRun to ExecuteSpecs;
    dependency 'DR-007 derives SR-021' from HeadlessSpecRun to CiReproducible;
    dependency 'DR-008 derives SR-016' from TraceIndex to TraceQuery;
    dependency 'DR-008 derives SR-021' from TraceIndex to CiReproducible;
    dependency 'DR-009 derives SR-013' from TraceRules to ModelTraceCompleteness;
    dependency 'DR-009 derives SR-014' from TraceRules to SpecTraceCompleteness;
    dependency 'DR-010 derives SR-016' from StaleReferenceDetection to TraceQuery;
    dependency 'DR-011 derives SR-005' from CoverageReportFormat to CoverageReport;
    dependency 'DR-011 derives SR-021' from CoverageReportFormat to CiReproducible;
    dependency 'DR-012 derives SR-030' from ApprovalRecord to ChangeRecords;
    dependency 'DR-012 derives SR-008' from ApprovalRecord to ApprovalGates;
    dependency 'DR-013 derives SR-031' from ApproverEligibility to SegregationOfDuties;
    dependency 'DR-014 derives SR-008' from GateEvaluation to ApprovalGates;
    dependency 'DR-014 derives SR-015' from GateEvaluation to TraceGateEnforcement;
    dependency 'DR-015 derives SR-015' from WaiverRecord to TraceGateEnforcement;
    dependency 'DR-015 derives SR-030' from WaiverRecord to ChangeRecords;
    dependency 'DR-016 derives SR-012' from ApprovalInvalidation to ApprovalReset;
    dependency 'DR-017 derives SR-010' from ImpactAnalysis to ChangeImpactAnalysis;
    dependency 'DR-018 derives SR-041' from TamperEvidentApprovals to TamperEvidentBaselines;
    dependency 'DR-018 derives SR-030' from TamperEvidentApprovals to ChangeRecords;
    dependency 'DR-019 derives SR-041' from DriftDetection to TamperEvidentBaselines;
    dependency 'DR-020 derives SR-032' from EvidenceBundle to RequirementsToTestEvidence;
    dependency 'DR-021 derives SR-007' from DecisionLogFormat to DecisionLog;
    dependency 'DR-021 derives SR-030' from DecisionLogFormat to ChangeRecords;
    dependency 'DR-022 derives SR-001' from WorkflowPrompts to QAndABeforeDrafting;
    dependency 'DR-022 derives SR-007' from WorkflowPrompts to DecisionLog;
    dependency 'DR-023 derives SR-042' from PathContainment to RestrictedFileAccess;
    dependency 'DR-024 derives SR-043' from UntrustedContentHandling to UntrustedInputHandling;
    dependency 'DR-032 derives SR-043' from HumanConfirmationChannel to UntrustedInputHandling;
    dependency 'DR-032 derives SR-045' from HumanConfirmationChannel to AiContributionMarked;
    dependency 'DR-025 derives SR-044' from ConfidentialityExclusions to NoSecretsToLlm;
    dependency 'DR-026 derives SR-040' from RefProtectionOutsideAgent to NoAgentWriteToBaseline;
    dependency 'DR-027 derives SR-009' from ViewExport to RenderViews;
    dependency 'DR-028 derives SR-022' from StableIdScheme to UnambiguousIds;
    dependency 'DR-029 derives SR-020' from OpenFormatsOnly to OpenFormats;
    dependency 'DR-030 derives SR-021' from HeadlessCli to CiReproducible;
    dependency 'DR-033 derives SR-017' from SourceTraceRules to RequirementSourceTraceability;
    dependency 'DR-034 derives SR-017' from SourceDeclaration to RequirementSourceTraceability;
    dependency 'DR-031 derives SR-032' from AuditQuery to RequirementsToTestEvidence;
    dependency 'DR-031 derives SR-030' from AuditQuery to ChangeRecords;
}
