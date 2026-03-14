"""Thin async helper for calling the ON24 MCP server from the backend."""
import json
import logging
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)


async def call_mcp_tool(tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Call a tool on the ON24 MCP server.

    Checks USE_MCP and blocklist before making the call.
    Raises RuntimeError if MCP is disabled or the tool is blocked.
    """
    if not settings.mcp_enabled:
        raise RuntimeError("MCP is disabled (USE_MCP != Y)")
    if tool_name in settings.mcp_blocklist:
        raise RuntimeError(f"Tool '{tool_name}' is in USE_MCP_BLOCKLIST")

    from mcp.client.streamable_http import streamablehttp_client
    from mcp import ClientSession

    url = f"{settings.mcp_server_url.rstrip('/')}/mcp"
    logger.info(f"Calling MCP tool '{tool_name}' at {url}")

    async with streamablehttp_client(url) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, arguments)

    # FastMCP returns result.content as a list of TextContent
    if result.content:
        text = result.content[0].text
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {"success": True, "message": text}
    return {"success": True}
