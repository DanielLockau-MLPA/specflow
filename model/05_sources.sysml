package ProjectSources {
    doc /* Requirement sources: where the needs come from (norm, written communication with a stakeholder, or other written document). Every need cites at least one source; every source names the stakeholder who raised or owns it. Use cases and requirements below the need level inherit their sources through the trace chain. */
    private import ProjectNeeds::*;

    item def RequirementSource {
        attribute kind : ScalarValues::String;
        attribute reference : ScalarValues::String;
    }

    item <'SRC-001'> ProjectBrief : RequirementSource {
        doc /* Requirements owner's initial request and Q&A, recorded in docs/sources/project-brief.md. */
        attribute :>> kind = "communication";
        attribute :>> reference = "docs/sources/project-brief.md";
    }
    item <'SRC-002'> Iso27001 : RequirementSource {
        doc /* Information security management requirements for an ISO/IEC 27001 certified organisation. */
        attribute :>> kind = "norm";
        attribute :>> reference = "ISO/IEC 27001";
    }
    item <'SRC-003'> Iso9001 : RequirementSource {
        doc /* Quality management requirements (documented information, traceability, change control) for an ISO 9001 certified organisation. */
        attribute :>> kind = "norm";
        attribute :>> reference = "ISO 9001";
    }
    item <'SRC-004'> Iec62443 : RequirementSource {
        doc /* Industrial automation and control systems security (access control, secure development lifecycle). */
        attribute :>> kind = "norm";
        attribute :>> reference = "IEC 62443";
    }

    dependency 'SRC-001 raisedBy STK-001' from ProjectBrief to RequirementsOwner;
    dependency 'SRC-002 raisedBy STK-006' from Iso27001 to InformationSecurity;
    dependency 'SRC-003 raisedBy STK-005' from Iso9001 to QualityManagement;
    dependency 'SRC-004 raisedBy STK-006' from Iec62443 to InformationSecurity;

    dependency 'N-001 cites SRC-001' from TurnRequirementsIntoDesign to ProjectBrief;
    dependency 'N-002 cites SRC-001' from AgreeOnDesign to ProjectBrief;
    dependency 'N-003 cites SRC-001' from DesignIncludesAllRequirementKinds to ProjectBrief;
    dependency 'N-004 cites SRC-001' from PreciselyTestableSpecification to ProjectBrief;
    dependency 'N-005 cites SRC-001' from EndToEndTraceability to ProjectBrief;
    dependency 'N-005 cites SRC-003' from EndToEndTraceability to Iso9001;
    dependency 'N-006 cites SRC-001' from VisualAndTextualModel to ProjectBrief;
    dependency 'N-007 cites SRC-001' from HumanControlOfAi to ProjectBrief;
    dependency 'N-007 cites SRC-004' from HumanControlOfAi to Iec62443;
    dependency 'N-008 cites SRC-001' from CertifiableWorkflow to ProjectBrief;
    dependency 'N-008 cites SRC-002' from CertifiableWorkflow to Iso27001;
    dependency 'N-008 cites SRC-003' from CertifiableWorkflow to Iso9001;
    dependency 'N-008 cites SRC-004' from CertifiableWorkflow to Iec62443;
    dependency 'N-009 cites SRC-001' from ToolAndLlmIndependence to ProjectBrief;
    dependency 'N-010 cites SRC-001' from ReproducibleChecks to ProjectBrief;
}
