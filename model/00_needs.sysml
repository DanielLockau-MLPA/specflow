package ProjectNeeds {
    doc /* Stakeholder needs (need level, solution-independent). Status: DRAFT. */

    requirement def Need {
        attribute status : ScalarValues::String;
        attribute rationale : ScalarValues::String;
    }

    part def Stakeholder;
    part RequirementsOwner : Stakeholder;
    part SystemsEngineer : Stakeholder;
    part Reviewer : Stakeholder;
    part AgentOperator : Stakeholder;
    part QualityManagement : Stakeholder;
    part InformationSecurity : Stakeholder;
    part ImplementationTeam : Stakeholder;

    requirement <'N-001'> TurnRequirementsIntoDesign : Need {
        doc /* Stakeholders need requirements (input documents and Q&A) turned into a reviewable system design, for software and non-software systems. */
    }
    requirement <'N-002'> AgreeOnDesign : Need {
        doc /* Stakeholders need to review, modify and formally approve the design until all agree. */
    }
    requirement <'N-003'> DesignIncludesAllRequirementKinds : Need {
        doc /* The approved design must cover functional, non-functional, normative and security (threat-derived) requirements and constraints. */
    }
    requirement <'N-004'> PreciselyTestableSpecification : Need {
        doc /* Implementers need a precise, executable specification consistent with the approved design, as the gate before implementation. */
    }
    requirement <'N-005'> EndToEndTraceability : Need {
        doc /* Quality management needs traceability from need to use case, requirement, design element, threat, scenario and approval. */
    }
    requirement <'N-006'> VisualAndTextualModel : Need {
        doc /* Reviewers need visual views of the model; engineers need diff-able text. */
    }
    requirement <'N-007'> HumanControlOfAi : Need {
        doc /* AI assistance must never change approved content or approve anything without human decision. */
    }
    requirement <'N-008'> CertifiableWorkflow : Need {
        doc /* The workflow must be acceptable in an ISO 27001, ISO 9001 and IEC 62443 certified company (records, access control, change control). */
    }
    requirement <'N-009'> ToolAndLlmIndependence : Need {
        doc /* The organisation must be able to exchange the AI client/LLM and modeling tools without losing model or specs. */
    }
    requirement <'N-010'> ReproducibleChecks : Need {
        doc /* Validation and coverage checks must be reproducible automatically (CI). */
    }
}
