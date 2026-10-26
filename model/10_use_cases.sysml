package ProjectUseCases {
    doc /* Use cases covering the needs. Status: DRAFT. */
    private import ProjectNeeds::*;
    private import SystemRequirements::*;

    part def AiAgent;
    part def ProjectSystem { doc /* The system of interest: MCP servers, validation/coverage tooling, decision log, gate enforcement. */ }
    part agent : AiAgent;

    use case <'UC-01'> ElicitRequirements {
        doc /* Requirements owner supplies inputs; agent runs a Q&A; both record an agreed requirement baseline (G1). */
        subject system : ProjectSystem { perform main.recordDecisions; }
        actor owner : Stakeholder { perform main.supplyInputs; perform main.answerQuestions; }
        actor ai : AiAgent { perform main.askQuestions; perform main.draftBaseline; perform altUntrustedInput; }
        actor reviewers : Stakeholder[1..*] { perform main.approveBaseline; perform altRejected; }
        objective { doc /* Agreed, baselined needs and requirements (G1). Precondition: input documents available. Postcondition: baseline tagged and decisions logged. */ }

        action main {
            action supplyInputs;
            then action askQuestions;
            then action answerQuestions;
            then action recordDecisions;
            then action draftBaseline;
            then action approveBaseline;
        }
        // Alternative: owner or reviewer rejects the draft
        action altRejected {
            doc /* From draftBaseline/approveBaseline: reviewer rejects; return to askQuestions with the rejection reason logged. */
        }
        // Failure: input contains instructions aimed at the agent
        action altUntrustedInput {
            doc /* Agent flags embedded instructions, ignores them, and asks the operator to confirm. */
        }
    }

    use case <'UC-02'> DraftModel {
        doc /* Agent drafts the SysML v2 model from the baseline; unresolved questions go to the decision log. */
        subject system : ProjectSystem { perform main.validateModel; perform altBaselineWriteAttempt; }
        actor ai : AiAgent { perform main.readBaseline; perform main.askClarifyingQuestions; perform main.proposeModelOnBranch; perform main.reportOpenQuestions; perform altValidationFails; }
        actor engineer : Stakeholder { perform main.answerQuestions; }
        objective { doc /* Draft model on a non-baseline branch. Precondition: G1 passed. Postcondition: draft validated, open questions logged. */ }

        action main {
            action readBaseline;
            then action askClarifyingQuestions;
            then action answerQuestions;
            then action proposeModelOnBranch;
            then action validateModel;
            then action reportOpenQuestions;
        }
        action altValidationFails {
            doc /* From validateModel: errors reported with location; agent corrects and re-validates; after repeated failure hands over to the engineer. */
        }
        action altBaselineWriteAttempt {
            doc /* Agent attempts to write to the approved baseline; the system denies and logs the attempt. */
        }
    }

    use case <'UC-03'> ReviewAndApproveModel {
        doc /* Review team modifies the model; all stakeholders approve (G2). */
        subject system : ProjectSystem { perform main.presentViews; perform main.checkCoverage; perform main.recordApprovals; perform main.tagBaseline; perform altCoverageGap; perform altAgentApproval; }
        actor engineer : Stakeholder { perform main.modifyModel; }
        actor reviewers : Stakeholder[1..*] { perform main.collectComments; perform altChangesRequested; }
        actor ai : AiAgent { doc /* May suggest edits during modifyModel on a branch; no approval rights. */ }
        objective { doc /* Model approved by all required roles (G2). Precondition: validated draft. Postcondition: approved baseline tagged, coverage complete. */ }

        action main {
            action presentViews;
            then action collectComments;
            then action modifyModel;
            then action checkCoverage;
            then action recordApprovals;
            then action tagBaseline;
        }
        action altChangesRequested {
            doc /* A reviewer requests changes; loop to modifyModel; earlier approvals are reset if the change affects approved elements. */
        }
        action altCoverageGap {
            doc /* checkCoverage lists gaps; gate G2 stays closed until resolved or waived by a recorded decision. */
        }
        action altAgentApproval {
            doc /* An approval attributed to the AI agent is rejected. */
        }
    }

    dependency 'UC-01 exercises SR-001' from ElicitRequirements to SystemRequirements::QAndABeforeDrafting;
    dependency 'UC-01 exercises SR-007' from ElicitRequirements to SystemRequirements::DecisionLog;
    dependency 'UC-01 exercises SR-043' from ElicitRequirements to SystemRequirements::UntrustedInputHandling;
    dependency 'UC-02 exercises SR-002' from DraftModel to SystemRequirements::DraftModelFromBaseline;
    dependency 'UC-02 exercises SR-004' from DraftModel to SystemRequirements::ValidateModel;
    dependency 'UC-02 exercises SR-040' from DraftModel to SystemRequirements::NoAgentWriteToBaseline;
    dependency 'UC-03 exercises SR-005' from ReviewAndApproveModel to SystemRequirements::CoverageReport;
    dependency 'UC-03 exercises SR-008' from ReviewAndApproveModel to SystemRequirements::ApprovalGates;
    dependency 'UC-03 exercises SR-009' from ReviewAndApproveModel to SystemRequirements::RenderViews;
    dependency 'UC-03 exercises SR-031' from ReviewAndApproveModel to SystemRequirements::SegregationOfDuties;

    use case <'UC-04'> ReviewModelWithAgent {
        doc /* Engineers and agent run a Q&A on the approved model to reach shared understanding. */
        subject system : ProjectSystem { perform main.provideModelContext; perform main.recordUnderstanding; }
        actor engineer : Stakeholder { perform main.answerQuestions; perform main.confirmUnderstanding; }
        actor ai : AiAgent { perform main.askQuestions; perform main.summariseModel; perform altModelDefectFound; }
        objective { doc /* Shared understanding of the model before specification work. Precondition: G2 passed. Postcondition: understanding and open points logged. */ }

        action main {
            action provideModelContext;
            then action summariseModel;
            then action askQuestions;
            then action answerQuestions;
            then action confirmUnderstanding;
            then action recordUnderstanding;
        }
        action altModelDefectFound {
            doc /* Agent finds an inconsistency or gap; it is logged and routed to UC-08, never fixed in the baseline directly. */
        }
    }

    use case <'UC-05'> DraftSpecification {
        doc /* Agent drafts executable specification from the model, tagged with model IDs. */
        subject system : ProjectSystem { perform main.provideModelElements; perform main.executeSpecs; perform main.reportCoverage; perform altNoScenarioPossible; }
        actor ai : AiAgent { perform main.draftScenarios; perform main.tagWithModelIds; }
        actor engineer : Stakeholder { perform main.reviewDraftHandover; }
        objective { doc /* Draft specification on a non-baseline branch. Precondition: G2 passed and UC-04 done. Postcondition: scenarios executable, tagged, gaps listed. */ }

        action main {
            action provideModelElements;
            then action draftScenarios;
            then action tagWithModelIds;
            then action executeSpecs;
            then action reportCoverage;
            then action reviewDraftHandover;
        }
        action altNoScenarioPossible {
            doc /* A requirement is not testable as written; it is flagged and routed to UC-08. */
        }
    }

    use case <'UC-06'> ReviewAndApproveSpecification {
        doc /* Review team modifies specs; all stakeholders approve (G3). */
        subject system : ProjectSystem { perform main.executeSpecs; perform main.checkCoverage; perform main.recordApprovals; perform main.tagBaseline; perform altSpecFails; perform altAgentApproval; }
        actor engineer : Stakeholder { perform main.modifySpecs; }
        actor reviewers : Stakeholder[1..*] { perform main.collectComments; perform altChangesRequested; }
        objective { doc /* Specification approved by all required roles (G3). Precondition: executable draft. Postcondition: baseline tagged, every requirement has a passing scenario or recorded waiver. */ }

        action main {
            action collectComments;
            then action modifySpecs;
            then action executeSpecs;
            then action checkCoverage;
            then action recordApprovals;
            then action tagBaseline;
        }
        action altChangesRequested { doc /* Loop to modifySpecs; approvals reset if approved items change. */ }
        action altSpecFails { doc /* Failing scenario blocks the gate until fixed or the spec/model is corrected via UC-08. */ }
        action altAgentApproval { doc /* An approval attributed to the AI agent is rejected. */ }
    }

    use case <'UC-07'> CheckCoverage {
        doc /* Anyone runs validation and coverage checks locally or in CI. */
        subject system : ProjectSystem { perform main.validateModel; perform main.computeCoverage; perform main.executeSpecs; perform main.publishReport; perform altNonDeterministic; }
        actor user : Stakeholder { perform main.startCheck; perform main.readReport; }
        objective { doc /* Reproducible validation and coverage report. Precondition: workspace checked out. Postcondition: report with gaps, exit status for CI. */ }

        action main {
            action startCheck;
            then action validateModel;
            then action computeCoverage;
            then action executeSpecs;
            then action publishReport;
            then action readReport;
        }
        action altNonDeterministic { doc /* Two runs on identical input differ; the check fails and reports the difference. */ }
    }

    use case <'UC-08'> ChangeApprovedBaseline {
        doc /* A change to approved content triggers impact analysis and re-approval. */
        subject system : ProjectSystem { perform main.analyseImpact; perform main.resetApprovals; perform main.recordApprovals; perform main.tagBaseline; perform altAgentWriteDenied; }
        actor requester : Stakeholder { perform main.requestChange; perform main.proposeChange; }
        actor ai : AiAgent { doc /* May propose changes on a branch only; marked as AI-authored. */ }
        actor reviewers : Stakeholder[1..*] { perform main.reviewChange; }
        objective { doc /* Controlled change with re-approval. Precondition: an approved baseline exists. Postcondition: new baseline tagged with change record, or change rejected. */ }

        action main {
            action requestChange;
            then action analyseImpact;
            then action proposeChange;
            then action reviewChange;
            then action resetApprovals;
            then action recordApprovals;
            then action tagBaseline;
        }
        action altAgentWriteDenied { doc /* Direct agent write to the baseline is denied and logged. */ }
    }

    use case <'UC-09'> ReviewSecurityConstraints {
        doc /* Information security reviews the security constraints and their traceability. */
        subject system : ProjectSystem { perform main.listSecurityRequirements; perform main.showTraceAndCoverage; perform main.recordApprovals; }
        actor securityReviewer : Stakeholder { perform main.assessConstraints; perform main.raiseFindings; }
        objective { doc /* Security constraints reviewed and approved or findings raised. Precondition: model draft exists. Postcondition: decision logged. */ }

        action main {
            action listSecurityRequirements;
            then action showTraceAndCoverage;
            then action assessConstraints;
            then action raiseFindings;
            then action recordApprovals;
        }
    }

    use case <'UC-10'> AuditHistory {
        doc /* Quality management inspects who approved what, when, on which baseline. */
        subject system : ProjectSystem { perform main.retrieveBaselines; perform main.showApprovalsAndChanges; perform main.verifyIntegrity; perform altIntegrityFailure; }
        actor auditor : Stakeholder { perform main.selectBaseline; perform main.inspectEvidence; }
        objective { doc /* Verifiable evidence of approvals, changes and test results per baseline. Precondition: baselines exist. Postcondition: audit findings recorded. */ }

        action main {
            action selectBaseline;
            then action retrieveBaselines;
            then action verifyIntegrity;
            then action showApprovalsAndChanges;
            then action inspectEvidence;
        }
        action altIntegrityFailure { doc /* Signature or hash check fails; reported as a security finding. */ }
    }

    use case <'UC-11'> VerifyTraceability {
        doc /* Any stakeholder verifies traceability at a chosen stage (needs, model, specification) and before gates G1 to G4. */
        subject system : ProjectSystem { perform main.selectScope; perform main.checkLinks; perform main.listGaps; perform main.applyWaivers; perform main.publishTraceReport; perform altDanglingReference; perform altWaiverInvalid; }
        actor verifier : Stakeholder { perform main.chooseStage; perform main.reviewTraceReport; perform main.decideOnGaps; }
        actor ai : AiAgent { doc /* May run the check and suggest fixes on a branch; cannot grant waivers. */ }
        objective { doc /* Evidence that traces are complete and current for the chosen stage. Precondition: workspace with the stage artifacts. Postcondition: trace report with gaps, waivers and result per gate. */ }

        action main {
            action chooseStage;
            then action selectScope;
            then action checkLinks;
            then action listGaps;
            then action reviewTraceReport;
            then action decideOnGaps;
            then action applyWaivers;
            then action publishTraceReport;
        }
        action altDanglingReference { doc /* A link targets a removed or renamed element ID; reported as a stale reference and the gate stays closed. */ }
        action altWaiverInvalid { doc /* A waiver lacks a human approver or rationale, or is attributed to the AI agent; it is rejected. */ }
    }

    dependency 'UC-01 covers N-001' from ElicitRequirements to TurnRequirementsIntoDesign;
    dependency 'UC-02 covers N-001' from DraftModel to TurnRequirementsIntoDesign;
    dependency 'UC-03 covers N-002' from ReviewAndApproveModel to AgreeOnDesign;
    dependency 'UC-03 covers N-003' from ReviewAndApproveModel to DesignIncludesAllRequirementKinds;
    dependency 'UC-04 covers N-002' from ReviewModelWithAgent to AgreeOnDesign;
    dependency 'UC-05 covers N-004' from DraftSpecification to PreciselyTestableSpecification;
    dependency 'UC-06 covers N-004' from ReviewAndApproveSpecification to PreciselyTestableSpecification;
    dependency 'UC-07 covers N-005' from CheckCoverage to EndToEndTraceability;
    dependency 'UC-07 covers N-010' from CheckCoverage to ReproducibleChecks;
    dependency 'UC-08 covers N-007' from ChangeApprovedBaseline to HumanControlOfAi;
    dependency 'UC-09 covers N-003' from ReviewSecurityConstraints to DesignIncludesAllRequirementKinds;
    dependency 'UC-11 covers N-005' from VerifyTraceability to EndToEndTraceability;
    dependency 'UC-10 covers N-008' from AuditHistory to CertifiableWorkflow;
    dependency 'UC-02 covers N-006' from DraftModel to VisualAndTextualModel;
    dependency 'UC-02 covers N-009' from DraftModel to ToolAndLlmIndependence;

    dependency 'UC-04 exercises SR-001' from ReviewModelWithAgent to SystemRequirements::QAndABeforeDrafting;
    dependency 'UC-04 exercises SR-007' from ReviewModelWithAgent to SystemRequirements::DecisionLog;
    dependency 'UC-05 exercises SR-003' from DraftSpecification to SystemRequirements::DraftSpecFromModel;
    dependency 'UC-05 exercises SR-006' from DraftSpecification to SystemRequirements::ExecuteSpecs;
    dependency 'UC-05 exercises SR-045' from DraftSpecification to SystemRequirements::AiContributionMarked;
    dependency 'UC-06 exercises SR-006' from ReviewAndApproveSpecification to SystemRequirements::ExecuteSpecs;
    dependency 'UC-06 exercises SR-008' from ReviewAndApproveSpecification to SystemRequirements::ApprovalGates;
    dependency 'UC-06 exercises SR-031' from ReviewAndApproveSpecification to SystemRequirements::SegregationOfDuties;
    dependency 'UC-07 exercises SR-004' from CheckCoverage to SystemRequirements::ValidateModel;
    dependency 'UC-07 exercises SR-005' from CheckCoverage to SystemRequirements::CoverageReport;
    dependency 'UC-03 exercises SR-015' from ReviewAndApproveModel to SystemRequirements::TraceGateEnforcement;
    dependency 'UC-06 exercises SR-015' from ReviewAndApproveSpecification to SystemRequirements::TraceGateEnforcement;
    dependency 'UC-07 exercises SR-021' from CheckCoverage to SystemRequirements::CiReproducible;
    dependency 'UC-08 exercises SR-010' from ChangeApprovedBaseline to SystemRequirements::ChangeImpactAnalysis;
    dependency 'UC-08 exercises SR-012' from ChangeApprovedBaseline to SystemRequirements::ApprovalReset;
    dependency 'UC-08 exercises SR-030' from ChangeApprovedBaseline to SystemRequirements::ChangeRecords;
    dependency 'UC-08 exercises SR-040' from ChangeApprovedBaseline to SystemRequirements::NoAgentWriteToBaseline;
    dependency 'UC-09 exercises SR-005' from ReviewSecurityConstraints to SystemRequirements::CoverageReport;
    dependency 'UC-10 exercises SR-030' from AuditHistory to SystemRequirements::ChangeRecords;
    dependency 'UC-10 exercises SR-032' from AuditHistory to SystemRequirements::RequirementsToTestEvidence;
    dependency 'UC-10 exercises SR-041' from AuditHistory to SystemRequirements::TamperEvidentBaselines;

    dependency 'UC-11 exercises SR-013' from VerifyTraceability to SystemRequirements::ModelTraceCompleteness;
    dependency 'UC-11 exercises SR-014' from VerifyTraceability to SystemRequirements::SpecTraceCompleteness;
    dependency 'UC-11 exercises SR-015' from VerifyTraceability to SystemRequirements::TraceGateEnforcement;
    dependency 'UC-11 exercises SR-016' from VerifyTraceability to SystemRequirements::TraceQuery;
    dependency 'UC-11 exercises SR-031' from VerifyTraceability to SystemRequirements::SegregationOfDuties;
}
