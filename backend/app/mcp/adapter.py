"""MCP Tool → Agent Tool adapter.

Converts MCP Tool JSON Schemas into AuraSaaS Agent Tool Schemas and
registers them into the global TOOL_SCHEMAS / TOOL_MAP registry.

When an MCP Server connects, its tools are dynamically discovered and
registered with privilege level 2 (analyze — safe for auto-selection).
"""

from __future__ import annotations

import json
import logging
from typing import Any

from app.mcp.client import InMemoryMCPServer, create_inmemory_mcp

logger = logging.getLogger(__name__)

MCP_TOOL_PREFIX = "mcp_"
DEFAULT_MCP_PRIVILEGE = 2  # analyze level — safe for auto-selection


def mcp_tool_to_agent_schema(mcp_tool: dict, server_name: str) -> dict:
    """Convert one MCP tool schema to AuraSaaS Agent tool schema.

    Returns a dict compatible with the ``TOOL_SCHEMAS`` list format:
    ``{name, description, parameters, privilege_level}``.
    """
    raw_name = mcp_tool.get("name", "unknown")
    agent_name = f"{MCP_TOOL_PREFIX}{server_name}__{raw_name}"
    description = mcp_tool.get("description", f"MCP tool: {raw_name}")
    input_schema = mcp_tool.get("inputSchema", {})

    # Normalize JSON Schema to OpenAI Function Calling parameters format
    parameters = {
        "type": input_schema.get("type", "object"),
        "properties": input_schema.get("properties", {}),
    }
    if "required" in input_schema:
        parameters["required"] = input_schema["required"]

    return {
        "type": "function",
        "function": {
            "name": agent_name,
            "description": f"[MCP:{server_name}] {description}",
            "parameters": parameters,
        },
        "privilege_level": DEFAULT_MCP_PRIVILEGE,
        "mcp_server": server_name,
        "mcp_tool_name": raw_name,
    }


def mcp_tools_to_agent_schemas(mcp_tools: list[dict], server_name: str) -> list[dict]:
    """Convert a list of MCP tools to Agent tool schemas."""
    return [mcp_tool_to_agent_schema(t, server_name) for t in mcp_tools]


# ── function-callable wrapper for MCP tools ───────────────────

class _MCPToolWrapper:
    """Callable wrapper that forwards Agent tool calls to an MCP server."""

    def __init__(self, server, tool_name: str):
        self._server = server
        self._tool_name = tool_name

    def __call__(self, **kwargs) -> dict:
        try:
            result = self._server.call_tool(self._tool_name, kwargs)
            return result
        except Exception as exc:
            return {"success": False, "error": str(exc)}


# ── registration into the Agent tool system ───────────────────

def register_mcp_tools(server, server_name: str) -> int:
    """Discover and register all tools from an MCP server into the Agent tool system.

    Args:
        server: An MCPClient or InMemoryMCPServer instance.
        server_name: Short name for the server (e.g. "filesystem").

    Returns:
        Number of tools registered.
    """
    from app.agents.tool_schemas import TOOL_SCHEMAS, TOOL_MAP

    try:
        mcp_tools = server.list_tools()
    except Exception as exc:
        logger.warning("Failed to list tools from MCP server '%s': %s", server_name, exc)
        return 0

    schemas = mcp_tools_to_agent_schemas(mcp_tools, server_name)
    count = 0
    for schema in schemas:
        agent_name = schema["function"]["name"]
        if agent_name not in TOOL_MAP:
            TOOL_SCHEMAS.append(schema)
            TOOL_MAP[agent_name] = _MCPToolWrapper(server, schema["mcp_tool_name"])
            count += 1

    logger.info("MCP %s: registered %d tools", server_name, count)
    return count


# ── startup helper ────────────────────────────────────────────

# Runtime registry of connected MCP servers (for cleanup at shutdown)
_mcp_servers: list = []


def init_mcp_servers(mcp_config: dict | None = None) -> list:
    """Initialize MCP servers from config and register their tools.

    Called at startup. If no real MCP servers are configured, creates
    in-memory fallback servers so the MCP tool registration flow still works.

    Config format:
        {"servers": [{"name": "filesystem", "command": ["npx", "-y", "..."], "env": {}}]}

    Returns:
        List of connected server instances.
    """
    global _mcp_servers
    servers = []

    if not mcp_config or not mcp_config.get("servers"):
        # No MCP servers configured — use in-memory fallback for demo
        logger.info("MCP: no servers configured, using in-memory fallback (filesystem + sqlite)")
        for name in ["filesystem", "sqlite"]:
            server = create_inmemory_mcp(name)
            servers.append(server)
            register_mcp_tools(server, name)
        _mcp_servers = servers
        return servers

    # Real MCP servers configured
    from app.mcp.client import MCPClient

    for cfg in mcp_config.get("servers", []):
        name = cfg.get("name", "unnamed")
        command = cfg.get("command", [])
        env = cfg.get("env")
        if not command:
            logger.warning("MCP %s: no command configured, skipping", name)
            continue
        try:
            client = MCPClient(name, command, env)
            client.connect()
            servers.append(client)
            register_mcp_tools(client, name)
        except Exception as exc:
            logger.warning("MCP %s: failed to connect: %s", name, exc)
            # Fall back to in-memory for this server
            server = create_inmemory_mcp(name)
            servers.append(server)
            register_mcp_tools(server, name)

    _mcp_servers = servers
    return servers


def shutdown_mcp_servers():
    """Disconnect all MCP servers. Called at shutdown."""
    global _mcp_servers
    for server in _mcp_servers:
        try:
            server.disconnect()
        except Exception:
            pass
    _mcp_servers = []
