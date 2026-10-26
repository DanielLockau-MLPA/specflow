"""In-process MCP client helpers for the step modules a_*.py (no steps defined here)."""
import asyncio

from mcp import Client, types

import mcp_model
import mcp_spec

SERVERS = {"model": mcp_model.mcp, "spec": mcp_spec.mcp}


def _client(server, approve):
    async def answer(ctx, params):
        return types.ElicitResult(action="accept", content={"approve": approve})

    return Client(SERVERS[server], elicitation_callback=answer, mode="legacy")


def call(server, tool, args=None, approve=True):
    """Call a tool; returns (is_error, text). A human answer is simulated through elicitation."""
    async def run():
        async with _client(server, approve) as c:
            r = await c.call_tool(tool, args or {})
            return r.is_error, "".join(x.text for x in r.content if hasattr(x, "text"))
    return asyncio.run(run())


def tool_names(server):
    async def run():
        async with _client(server, True) as c:
            return [t.name for t in (await c.list_tools()).tools]
    return asyncio.run(run())


def prompt_text(server, name):
    async def run():
        async with _client(server, True) as c:
            res = await c.get_prompt(name)
            return "\n".join(m.content.text for m in res.messages)
    return asyncio.run(run())
