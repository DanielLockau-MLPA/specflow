# SPDX-FileCopyrightText: (C) 2026 ML!PA Consulting GmbH
# SPDX-License-Identifier: MIT

"""In-process MCP client helpers for the step files of features 08 and 09 (no steps defined here)."""
import asyncio
import json

from mcp import Client, types

import mcp_model
import mcp_spec

SERVERS = {"model": mcp_model.mcp, "spec": mcp_spec.mcp}


def answer(action="accept", approve=True, delay=0.0, seen=None):
    """Elicitation callback standing in for the human's confirmation UI."""
    async def cb(ctx, params):
        if seen is not None:
            seen.append(params.message)
        if delay:
            await asyncio.sleep(delay)
        return types.ElicitResult(action=action, content={"approve": approve} if action == "accept" else None)
    return cb


def call(server, name, args, cb=None):
    """Call a tool; returns (is_error, text). Without `cb` the session has no confirmation channel."""
    async def run():
        async with Client(server, elicitation_callback=cb, mode="legacy") as c:
            r = await c.call_tool(name, args)
            return r.is_error, "".join(x.text for x in r.content if isinstance(x, types.TextContent))
    return asyncio.run(run())


def list_tools(server):
    async def run():
        async with Client(server, mode="legacy") as c:
            return (await c.list_tools()).tools
    return asyncio.run(run())


def parse(text):
    return json.loads(text)
