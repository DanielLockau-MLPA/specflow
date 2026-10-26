"""Tools shared by the model and spec MCP servers: guarded document reads, decisions and proposals.

The functions here are the InputGuard behaviour of the prototype (DR-024): file access goes through
Workspace, content is filtered and labelled, and every state-changing tool asks the human first (DR-032).
"""
from mcp.server.mcpserver import Context

import specflow_core as core


def register_common(mcp):
    @mcp.tool()
    def read_document(path: str) -> dict:
        """Read an input document. The content is returned labelled as untrusted data."""
        ws = core.Workspace()
        p = ws.resolve(path)
        rel = p.relative_to(ws.root).as_posix()
        return core.untrusted(rel, core.filter_content(rel, p.read_text(encoding="utf-8"), ws))

    @mcp.tool()
    def list_decisions(stage: str) -> str:
        """Return the decision log of a stage ('model' or 'spec')."""
        return core.list_decisions(stage)

    @mcp.tool()
    async def record_decision(stage: str, kind: str, participants: list[str], question: str, decision: str,
                              rationale: str, affected: list[str], ctx: Context) -> str:
        """Append a Q&A or review outcome to the decision log (kind 'qa' or 'review'). Needs human confirmation."""
        unknown = [a for a in affected if a not in core.model_ids()]
        if unknown:
            raise core.Rejected(f"unknown element ID: {', '.join(unknown)}")
        await core.confirm(ctx, f"Record {kind} decision for stage '{stage}': {decision}")
        return core.record_decision(stage, kind, participants, question, decision, rationale, affected)

    @mcp.tool()
    async def propose_edit(path: str, content: str, branch: str, message: str, ctx: Context) -> dict:
        """Commit a change to a proposal/* branch. Never writes to baselines. Needs human confirmation."""
        ws = core.Workspace()
        ws.resolve(path)
        if not branch.startswith("proposal/"):
            raise core.Rejected("writes are only accepted on branches matching proposal/*")
        await core.confirm(ctx, f"Commit {path} to branch {branch}: {message}")
        return {"branch": branch, "commit": core.propose_edit(path, content, branch, message), "status": "DRAFT"}
