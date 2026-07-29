"""MCP (Model Context Protocol) integration for AuraSaaS.

Lightweight MCP client that connects to MCP Servers via stdio or HTTP,
discovers their tools, and registers them into the Agent tool system.
"""

from app.mcp.client import MCPClient
from app.mcp.adapter import mcp_tools_to_agent_schemas, register_mcp_tools

__all__ = ["MCPClient", "mcp_tools_to_agent_schemas", "register_mcp_tools"]
