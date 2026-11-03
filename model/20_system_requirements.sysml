package SystemRequirements {
    doc /* L1 system requirements. Kinds: functional, quality, normative, security (constraints). */
    private import ProjectNeeds::*;
    private import ProjectUseCases::*;

    enum def Kind { enum functional; enum quality; enum normative; enum security; }

    requirement def SystemRequirement {
        attribute kind : Kind;
        attribute status : ScalarValues::String;
    }

    // Functional
    requirement <'SR-001'> QAndABeforeDrafting : SystemRequirement {
        doc /* The system shall support a recorded Q&A between humans and the agent before the agent drafts the model, and again before it drafts the specification. */
        attribute :>> kind = Kind::functional;
    }
    requirement <'SR-002'> DraftModelFromBaseline : SystemRequirement {
        doc /* The system shall let the agent draft a SysML v2 model from an approved requirement baseline. */
        attribute :>> kind = Kind::functional;
    }
    requirement <'SR-003'> DraftSpecFromModel : SystemRequirement {
        doc /* The system shall let the agent draft an executable specification from an approved model, with each scenario referencing the IDs of the model elements it verifies. */
        attribute :>> kind = Kind::functional;
    }
    requirement <'SR-004'> ValidateModel : SystemRequirement {
        doc /* The system shall validate model syntax and semantics and report errors with element and file location. */
        attribute :>> kind = Kind::functional;
    }
    requirement <'SR-005'> CoverageReport : SystemRequirement {
        doc /* The system shall report coverage along need, use case, requirement, design element and scenario, and list every gap. */
        attribute :>> kind = Kind::functional;
    }
    requirement <'SR-006'> ExecuteSpecs : SystemRequirement {
        doc /* The system shall execute the specification and report pass/fail per scenario with its requirement IDs. */
        attribute :>> kind = Kind::functional;
    }
    requirement <'SR-007'> DecisionLog : SystemRequirement {
        doc /* The system shall record Q&A outcomes and review decisions in a decision log linked to the affected element IDs. */
        attribute :>> kind = Kind::functional;
    }
    requirement <'SR-008'> ApprovalGates : SystemRequirement {
        doc /* The system shall enforce gates G1 to G4; a gate opens only after recorded approval by every required stakeholder role. */
        attribute :>> kind = Kind::functional;
    }
    requirement <'SR-009'> RenderViews : SystemRequirement {
        doc /* The system shall provide graphical views of the model and text-based source in diff-able form. */
        attribute :>> kind = Kind::functional;
    }
    requirement <'SR-010'> ChangeImpactAnalysis : SystemRequirement {
        doc /* The system shall list all elements and scenarios affected by a change to an approved element and require re-approval. */
        attribute :>> kind = Kind::functional;
    }
    requirement <'SR-011'> AgentAccessViaMcp : SystemRequirement {
        doc /* The system shall expose model and specification operations to any compliant MCP client. */
        attribute :>> kind = Kind::functional;
    }

    requirement <'SR-012'> ApprovalReset : SystemRequirement {
        doc /* When approved content changes, the system shall invalidate every approval of the affected gate, keep the invalidated approvals in the history, and show which elements and scenarios are affected. */
        attribute :>> kind = Kind::functional;
    }

    requirement <'SR-013'> ModelTraceCompleteness : SystemRequirement {
        doc /* The system shall check that within the model every need is covered by at least one use case, every use case exercises at least one requirement, every L1 requirement derives from a need, every L2 requirement derives from an L1 requirement, and every L2 requirement is allocated to a design element; violations shall be reported as orphans or gaps. */
        attribute :>> kind = Kind::functional;
    }
    requirement <'SR-014'> SpecTraceCompleteness : SystemRequirement {
        doc /* The system shall check that every requirement is verified by at least one scenario and every scenario references at least one existing model element ID; scenarios without valid references and requirements without scenarios shall be reported. */
        attribute :>> kind = Kind::functional;
    }
    requirement <'SR-015'> TraceGateEnforcement : SystemRequirement {
        doc /* The system shall keep gates G2 and G3 closed while trace checks report gaps, unless each gap is waived by a recorded decision with approver and rationale. */
        attribute :>> kind = Kind::functional;
    }
    requirement <'SR-016'> TraceQuery : SystemRequirement {
        doc /* The system shall answer trace queries in both directions between any two levels (need, use case, requirement, element, scenario, test result) and detect dangling or stale references after changes. */
        attribute :>> kind = Kind::functional;
    }
    requirement <'SR-017'> RequirementSourceTraceability : SystemRequirement {
        doc /* The system shall record the sources of the needs (norms, written communication with a stakeholder, other written documents) together with the stakeholder who raised each source, and shall check that every need cites at least one source, every source names a stakeholder and is cited by a need, and that every use case and requirement reaches a source through its trace chain. */
        attribute :>> kind = Kind::functional;
    }
    requirement <'SR-018'> NoUnexecutedImplementation : SystemRequirement {
        doc /* The system shall report every function of the implementation that no executed scenario entered, and the implementation gate shall stay closed while such functions exist, unless each is listed with a reason in an allowlist that is part of the approved specification. */
        attribute :>> kind = Kind::functional;
    }

    // Quality
    requirement <'SR-020'> OpenFormats : SystemRequirement {
        doc /* Model, specs and logs shall be stored in open, text-based formats that do not require a specific agent or vendor tool. */
        attribute :>> kind = Kind::quality;
    }
    requirement <'SR-021'> CiReproducible : SystemRequirement {
        doc /* Validation, coverage and spec execution shall run headless with identical results for identical inputs. */
        attribute :>> kind = Kind::quality;
    }
    requirement <'SR-022'> UnambiguousIds : SystemRequirement {
        doc /* Every need, requirement source, stakeholder, use case, requirement, design element and scenario shall have a stable unique ID that survives renaming. */
        attribute :>> kind = Kind::quality;
    }

    // Normative (ISO 27001, ISO 9001, IEC 62443)
    requirement <'SR-030'> ChangeRecords : SystemRequirement {
        doc /* Every change to a baselined item shall be attributable (who, when, why, approver) and retained (ISO 9001 change control, ISO 27001 change management). */
        attribute :>> kind = Kind::normative;
    }
    requirement <'SR-031'> SegregationOfDuties : SystemRequirement {
        doc /* The author of a change shall not be its sole approver, and an AI agent shall never count as an approver. */
        attribute :>> kind = Kind::normative;
    }
    requirement <'SR-032'> RequirementsToTestEvidence : SystemRequirement {
        doc /* The system shall retain verifiable evidence linking each requirement to its test results per baseline (ISO 9001 design verification, IEC 62443-4-1). */
        attribute :>> kind = Kind::normative;
    }

    // Security (constraints)
    requirement <'SR-040'> NoAgentWriteToBaseline : SystemRequirement {
        doc /* Agents shall only propose changes on non-baseline branches; approved baselines shall be writable only through the approval process. */
        attribute :>> kind = Kind::security;
    }
    requirement <'SR-041'> TamperEvidentBaselines : SystemRequirement {
        doc /* Approvals shall be tamper-evident (signed, verifiable against registered keys) and drift of approved model and specification content shall be detected. */
        attribute :>> kind = Kind::security;
    }
    requirement <'SR-042'> RestrictedFileAccess : SystemRequirement {
        doc /* MCP tools shall only access paths inside the project workspace; path traversal shall be rejected. */
        attribute :>> kind = Kind::security;
    }
    requirement <'SR-043'> UntrustedInputHandling : SystemRequirement {
        doc /* Requirement documents and other inputs shall be treated as untrusted data; instructions inside them shall not trigger tool actions without human confirmation. */
        attribute :>> kind = Kind::security;
    }
    requirement <'SR-044'> NoSecretsToLlm : SystemRequirement {
        doc /* Content marked confidential or containing secrets shall not be sent to the LLM provider; the operator shall be able to configure exclusions. */
        attribute :>> kind = Kind::security;
    }
    requirement <'SR-045'> AiContributionMarked : SystemRequirement {
        doc /* AI-authored changes shall be identifiable in history and remain unapproved until reviewed by a human. */
        attribute :>> kind = Kind::security;
    }

    // Derivation: L1 -> Need
    dependency 'SR-013 derives N-005' from ModelTraceCompleteness to EndToEndTraceability;
    dependency 'SR-014 derives N-005' from SpecTraceCompleteness to EndToEndTraceability;
    dependency 'SR-015 derives N-002' from TraceGateEnforcement to AgreeOnDesign;
    dependency 'SR-016 derives N-005' from TraceQuery to EndToEndTraceability;
    dependency 'SR-017 derives N-005' from RequirementSourceTraceability to EndToEndTraceability;
    dependency 'SR-017 derives N-008' from RequirementSourceTraceability to CertifiableWorkflow;
    dependency 'SR-018 derives N-004' from NoUnexecutedImplementation to PreciselyTestableSpecification;
    dependency 'SR-018 derives N-010' from NoUnexecutedImplementation to ReproducibleChecks;
    dependency 'SR-012 derives N-002' from ApprovalReset to AgreeOnDesign;
    dependency 'SR-001 derives N-001' from QAndABeforeDrafting to TurnRequirementsIntoDesign;
    dependency 'SR-002 derives N-001' from DraftModelFromBaseline to TurnRequirementsIntoDesign;
    dependency 'SR-003 derives N-004' from DraftSpecFromModel to PreciselyTestableSpecification;
    dependency 'SR-004 derives N-010' from ValidateModel to ReproducibleChecks;
    dependency 'SR-005 derives N-005' from CoverageReport to EndToEndTraceability;
    dependency 'SR-006 derives N-004' from ExecuteSpecs to PreciselyTestableSpecification;
    dependency 'SR-007 derives N-005' from DecisionLog to EndToEndTraceability;
    dependency 'SR-008 derives N-002' from ApprovalGates to AgreeOnDesign;
    dependency 'SR-009 derives N-006' from RenderViews to VisualAndTextualModel;
    dependency 'SR-010 derives N-005' from ChangeImpactAnalysis to EndToEndTraceability;
    dependency 'SR-011 derives N-009' from AgentAccessViaMcp to ToolAndLlmIndependence;
    dependency 'SR-020 derives N-009' from OpenFormats to ToolAndLlmIndependence;
    dependency 'SR-021 derives N-010' from CiReproducible to ReproducibleChecks;
    dependency 'SR-022 derives N-005' from UnambiguousIds to EndToEndTraceability;
    dependency 'SR-030 derives N-008' from ChangeRecords to CertifiableWorkflow;
    dependency 'SR-031 derives N-008' from SegregationOfDuties to CertifiableWorkflow;
    dependency 'SR-031 derives N-007' from SegregationOfDuties to HumanControlOfAi;
    dependency 'SR-032 derives N-008' from RequirementsToTestEvidence to CertifiableWorkflow;
    dependency 'SR-040 derives N-007' from NoAgentWriteToBaseline to HumanControlOfAi;
    dependency 'SR-041 derives N-008' from TamperEvidentBaselines to CertifiableWorkflow;
    dependency 'SR-042 derives N-008' from RestrictedFileAccess to CertifiableWorkflow;
    dependency 'SR-043 derives N-007' from UntrustedInputHandling to HumanControlOfAi;
    dependency 'SR-044 derives N-008' from NoSecretsToLlm to CertifiableWorkflow;
    dependency 'SR-045 derives N-007' from AiContributionMarked to HumanControlOfAi;
}
