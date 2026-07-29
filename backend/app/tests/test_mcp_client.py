"""Tests for MCP Client — in-memory fallback and adapter."""

import pytest
from app.mcp.client import (
    InMemoryMCPServer,
    create_inmemory_mcp,
    FILESYSTEM_MCP_TOOLS,
    SQLITE_MCP_TOOLS,
)


def test_inmemory_server_list_tools():
    server = create_inmemory_mcp("filesystem")
    tools = server.list_tools()
    assert len(tools) == 4
    tool_names = {t["name"] for t in tools}
    assert "read_file" in tool_names
    assert "write_file" in tool_names
    assert "list_directory" in tool_names
    assert "search_files" in tool_names


def test_inmemory_server_call_tool():
    server = create_inmemory_mcp("filesystem")
    result = server.call_tool("read_file", {"path": "/tmp/test.txt"})
    assert result["success"] is True
    assert "in-memory fallback" in result["data"]


def test_inmemory_server_sqlite_tools():
    server = create_inmemory_mcp("sqlite")
    tools = server.list_tools()
    tool_names = {t["name"] for t in tools}
    assert "query" in tool_names
    assert "list_tables" in tool_names
    assert "describe_table" in tool_names


def test_inmemory_server_is_connected():
    server = create_inmemory_mcp("filesystem")
    assert server.is_connected is True


def test_inmemory_server_disconnect_noop():
    server = create_inmemory_mcp("filesystem")
    server.disconnect()  # should not raise


def test_filesystem_tools_have_schema():
    for tool in FILESYSTEM_MCP_TOOLS:
        assert "name" in tool
        assert "description" in tool
        assert "inputSchema" in tool
        assert "type" in tool["inputSchema"]


def test_sqlite_tools_have_schema():
    for tool in SQLITE_MCP_TOOLS:
        assert "name" in tool
        assert "inputSchema" in tool
