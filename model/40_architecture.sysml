package Architecture {
    doc /* Logical architecture of the system of interest, its external context, and the allocation of L2 requirements (satisfy). Status: DRAFT. Technology choices are bindings, not part of the logical structure. */
    private import DesignRequirements::*;

    // Interfaces
    port def McpPort { doc /* MCP (stdio or HTTP) endpoint: requests from the client and responses/prompts to it. */ }
    port def WorkspacePort { doc /* Read/write access to workspace files. */ }
    port def GitPort { doc /* Branch, commit, signed tag and ref operations. */ }
    port def TraceQueryPort { doc /* Trace graph queries and rule evaluation. */ }
    port def ContentPort { doc /* Content returned from tools towards the agent (to be filtered and labelled). */ }
    port def ConfirmationPort { doc /* Request for explicit human confirmation of a state-changing action. */ }
    port def HumanPort { doc /* Out-of-band interaction with a human (client confirmation dialog or terminal prompt) that the agent cannot answer. */ }
    port def CliPort { doc /* Command-line interaction of a human or CI job. */ }
    port def ApprovalPort { doc /* Submission and query of approvals, waivers and invalidations. */ }
    port def GatePort { doc /* Gate evaluation requests and results. */ }
    port def ImpactPort { doc /* Impact analysis requests and results. */ }
    port def RunPort { doc /* Execution of specifications and results. */ }
    port def LogPort { doc /* Appending to and reading from the decision log. */ }
    port def IdPort { doc /* Allocation and uniqueness checks of IDs. */ }
    port def ViewPort { doc /* Diagram and view export requests. */ }

    // Components of the system of interest
    part def ModelMcpServer {
        port mcp : McpPort; port content : ContentPort; port confirm : ConfirmationPort;
        port ws : WorkspacePort; port git : GitPort; port trace : TraceQueryPort;
        port impact : ImpactPort; port log : LogPort; port ids : IdPort; port views : ViewPort;
    }
    part def SpecMcpServer {
        port mcp : McpPort; port content : ContentPort; port confirm : ConfirmationPort;
        port ws : WorkspacePort; port git : GitPort; port trace : TraceQueryPort;
        port impact : ImpactPort; port log : LogPort; port ids : IdPort; port run : RunPort;
    }
    part def SpecRunner { port run : RunPort[*]; port ws : WorkspacePort; }
    part def TraceService { port query : TraceQueryPort[*]; port ws : WorkspacePort; }
    part def ImpactAnalyzer { port impact : ImpactPort[*]; port trace : TraceQueryPort; }
    part def ApprovalService { port approvals : ApprovalPort[*]; port git : GitPort; port trace : TraceQueryPort; port impact : ImpactPort; }
    part def GateEvaluator { port gates : GatePort[*]; port approvals : ApprovalPort; port trace : TraceQueryPort; }
    part def BaselineStore { port git : GitPort; port ws : WorkspacePort; port gate : GatePort; }
    part def DecisionLogService { port log : LogPort[*]; port ws : WorkspacePort; }
    part def PromptLibrary { port mcp : McpPort; }
    part def IdRegistry { port ids : IdPort[*]; port ws : WorkspacePort; }
    part def ViewExporter { port views : ViewPort; port ws : WorkspacePort; }
    part def ReviewCli {
        port human : CliPort; port trace : TraceQueryPort; port approvals : ApprovalPort;
        port gate : GatePort; port impact : ImpactPort; port run : RunPort;
    }
    part def WorkspaceGuard {
        doc /* Single entry to the file system: components connect here and are limited to the canonical workspace root. */
        port clients : WorkspacePort[*]; port files : WorkspacePort;
    }
    part def ConfidentialityFilter {
        doc /* Removes excluded or classified content before it reaches the agent. */
        port fromServers : ContentPort[*]; port toGuard : ContentPort;
    }
    part def InputGuard {
        doc /* Fronts all agent-facing MCP traffic: labels untrusted content and demands human confirmation for state changes. */
        port toAgent : McpPort; port servers : McpPort[*]; port fromFilter : ContentPort;
        port confirmations : ConfirmationPort[*]; port toChannel : ConfirmationPort;
    }
    part def ConfirmationChannel {
        doc /* Presents the confirmation request to the human outside the agent session and returns only the human's decision. */
        port fromGuard : ConfirmationPort; port toHuman : HumanPort;
    }

    // External context (outside the system boundary)
    part def Human { port cli : CliPort; port confirm : HumanPort; }
    part def McpClient { doc /* Any MCP client hosting the AI agent. Outside the boundary. */ port mcp : McpPort; }
    part def GitRepository { doc /* Workspace and version control, including host-side ref protection. Outside the boundary. */ port files : WorkspacePort; port git : GitPort[*]; }

    part def Toolchain {
        part modelMcp : ModelMcpServer;
        part specMcp : SpecMcpServer;
        part specRunner : SpecRunner;
        part traceService : TraceService;
        part impactAnalyzer : ImpactAnalyzer;
        part approvalService : ApprovalService;
        part gateEvaluator : GateEvaluator;
        part baselineStore : BaselineStore;
        part decisionLog : DecisionLogService;
        part promptLibrary : PromptLibrary;
        part workspaceGuard : WorkspaceGuard;
        part inputGuard : InputGuard;
        part confidentialityFilter : ConfidentialityFilter;
        part confirmationChannel : ConfirmationChannel;
        part idRegistry : IdRegistry;
        part reviewCli : ReviewCli;
        part viewExporter : ViewExporter;

        // Trace and analysis
        connect modelMcp.trace to traceService.query;
        connect specMcp.trace to traceService.query;
        connect impactAnalyzer.trace to traceService.query;
        connect approvalService.trace to traceService.query;
        connect gateEvaluator.trace to traceService.query;
        connect reviewCli.trace to traceService.query;
        connect modelMcp.impact to impactAnalyzer.impact;
        connect specMcp.impact to impactAnalyzer.impact;
        connect reviewCli.impact to impactAnalyzer.impact;
        connect approvalService.impact to impactAnalyzer.impact;

        // Approvals, gates, baselines (human-driven; no agent-facing port)
        connect gateEvaluator.approvals to approvalService.approvals;
        connect reviewCli.approvals to approvalService.approvals;
        connect reviewCli.gate to gateEvaluator.gates;
        connect baselineStore.gate to gateEvaluator.gates;

        // Spec execution, log, IDs, views
        connect specMcp.run to specRunner.run;
        connect reviewCli.run to specRunner.run;
        connect modelMcp.log to decisionLog.log;
        connect specMcp.log to decisionLog.log;
        connect modelMcp.ids to idRegistry.ids;
        connect specMcp.ids to idRegistry.ids;
        connect modelMcp.views to viewExporter.views;

        // File access only through the workspace guard
        connect modelMcp.ws to workspaceGuard.clients;
        connect specMcp.ws to workspaceGuard.clients;
        connect specRunner.ws to workspaceGuard.clients;
        connect traceService.ws to workspaceGuard.clients;
        connect baselineStore.ws to workspaceGuard.clients;
        connect decisionLog.ws to workspaceGuard.clients;
        connect idRegistry.ws to workspaceGuard.clients;
        connect viewExporter.ws to workspaceGuard.clients;

        // Agent-facing traffic: all MCP endpoints sit behind the input guard
        connect inputGuard.servers to modelMcp.mcp;
        connect inputGuard.servers to specMcp.mcp;
        connect inputGuard.servers to promptLibrary.mcp;
        connect modelMcp.content to confidentialityFilter.fromServers;
        connect specMcp.content to confidentialityFilter.fromServers;
        connect confidentialityFilter.toGuard to inputGuard.fromFilter;

        // Human confirmation of state-changing tools
        connect modelMcp.confirm to inputGuard.confirmations;
        connect specMcp.confirm to inputGuard.confirmations;
        connect inputGuard.toChannel to confirmationChannel.fromGuard;
    }

    part def SystemContext {
        part toolchain : Toolchain;
        part human : Human;
        part mcpClient : McpClient;
        part repo : GitRepository;

        connect mcpClient.mcp to toolchain.inputGuard.toAgent;
        connect toolchain.confirmationChannel.toHuman to human.confirm;
        connect human.cli to toolchain.reviewCli.human;
        connect toolchain.workspaceGuard.files to repo.files;
        connect toolchain.modelMcp.git to repo.git;
        connect toolchain.specMcp.git to repo.git;
        connect toolchain.approvalService.git to repo.git;
        connect toolchain.baselineStore.git to repo.git;
    }

    part context : SystemContext;

    // Allocation
    satisfy ModelMcpTools by context.toolchain.modelMcp;
    satisfy ValidationWithLocation by context.toolchain.modelMcp;
    satisfy ProposeOnBranchOnly by context.toolchain.modelMcp;
    satisfy ProposeOnBranchOnly by context.toolchain.specMcp;
    satisfy AiAuthorshipMarking by context.toolchain.modelMcp;
    satisfy AiAuthorshipMarking by context.toolchain.specMcp;
    satisfy SpecMcpTools by context.toolchain.specMcp;
    satisfy ScenarioIdTags by context.toolchain.specMcp;
    satisfy HeadlessSpecRun by context.toolchain.specRunner;
    satisfy TraceIndex by context.toolchain.traceService;
    satisfy TraceRules by context.toolchain.traceService;
    satisfy StaleReferenceDetection by context.toolchain.traceService;
    satisfy CoverageReportFormat by context.toolchain.traceService;
    satisfy ApprovalRecord by context.toolchain.approvalService;
    satisfy ApproverEligibility by context.toolchain.approvalService;
    satisfy GateEvaluation by context.toolchain.gateEvaluator;
    satisfy WaiverRecord by context.toolchain.approvalService;
    satisfy ApprovalInvalidation by context.toolchain.approvalService;
    satisfy ImpactAnalysis by context.toolchain.impactAnalyzer;
    satisfy SignedBaselineTags by context.toolchain.baselineStore;
    satisfy DriftDetection by context.toolchain.baselineStore;
    satisfy EvidenceBundle by context.toolchain.baselineStore;
    satisfy DecisionLogFormat by context.toolchain.decisionLog;
    satisfy WorkflowPrompts by context.toolchain.promptLibrary;
    satisfy PathContainment by context.toolchain.workspaceGuard;
    satisfy UntrustedContentHandling by context.toolchain.inputGuard;
    satisfy ConfidentialityExclusions by context.toolchain.confidentialityFilter;
    satisfy HumanConfirmationChannel by context.toolchain.confirmationChannel;
    satisfy RefProtectionOutsideAgent by context.toolchain.baselineStore;
    satisfy ViewExport by context.toolchain.viewExporter;
    satisfy StableIdScheme by context.toolchain.idRegistry;
    satisfy OpenFormatsOnly by context.toolchain;
    satisfy HeadlessCli by context.toolchain.reviewCli;
    satisfy AuditQuery by context.toolchain.reviewCli;
}
