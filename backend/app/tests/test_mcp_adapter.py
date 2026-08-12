"""Tests for MCP Tool → Agent Tool adapter."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "backend"))

import pytest
from app.mcp.adapter import (
    mcp_tool_to_agent_schema,
    mcp_tools_to_agent_schemas,
    register_mcp_tools,
)
from app.mcp.client import create_inmemory_mcp


def test_mcp_tool_to_agent_schema():
    mcp_tool = {
        "name": "read_file",
        "description": "Read a file",
        "inputSchema": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
        },
    }
    schema = mcp_tool_to_agent_schema(mcp_tool, "filesystem")
    assert schema["type"] == "function"
    assert schema["function"]["name"] == "mcp_filesystem__read_file"
    assert "[MCP:filesystem]" in schema["function"]["description"]
    assert schema["privilege_level"] == 2
    assert "path" in schema["function"]["parameters"]["properties"]


def test_mcp_tools_to_agent_schemas_batch():
    mcp_tools = [
        {"name": "t1", "description": "d1", "inputSchema": {"type": "object", "properties": {}}},
        {"name": "t2", "description": "d2", "inputSchema": {"type": "object", "properties": {}}},
    ]
    schemas = mcp_tools_to_agent_schemas(mcp_tools, "test")
    assert len(schemas) == 2
    assert schemas[0]["function"]["name"] == "mcp_test__t1"
    assert schemas[1]["function"]["name"] == "mcp_test__t2"


def test_register_mcp_tools():
    server = create_inmemory_mcp("filesystem")
    count = register_mcp_tools(server, "filesystem")
    assert count == 4

    from app.agents.tool_schemas import TOOL_MAP
    assert "mcp_filesystem__read_file" in TOOL_MAP
    assert "mcp_filesystem__write_file" in TOOL_MAP


def test_register_mcp_tools_idempotent():
    """Registering the same tools twice should not duplicate them."""
    from app.agents.tool_schemas import TOOL_SCHEMAS, TOOL_MAP

    # Save and clear existing MCP registrations
    saved_schemas = [s for s in TOOL_SCHEMAS if not s.get("mcp_server")]
    saved_map = {k: v for k, v in TOOL_MAP.items() if not k.startswith("mcp_")}
    TOOL_SCHEMAS[:] = saved_schemas
    TOOL_MAP.clear()
    TOOL_MAP.update(saved_map)

    server = create_inmemory_mcp("filesystem")
    count1 = register_mcp_tools(server, "filesystem")
    assert count1 == 4
    count2 = register_mcp_tools(server, "filesystem")
    assert count2 == 0  # all already registered


def test_mcp_tool_wrapper_callable():
    """The registered MCP tool should be callable."""
    from app.agents.tool_schemas import TOOL_MAP

    server = create_inmemory_mcp("filesystem")
    register_mcp_tools(server, "filesystem")

    fn = TOOL_MAP.get("mcp_filesystem__read_file")
    assert fn is not None
    assert callable(fn)

    result = fn(path="/tmp/test.txt")
    assert result["success"] is True
