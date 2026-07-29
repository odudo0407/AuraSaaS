"""Lightweight MCP Client — JSON-RPC over stdio.

Connects to an MCP Server process (stdio transport), performs the
initialize handshake, discovers tools via ``tools/list``, and calls
tools via ``tools/call``.

Does NOT require the official ``mcp`` SDK — implements the protocol
directly for transparency and zero-dependency deployment.
"""

from __future__ import annotations

import json
import logging
import subprocess
import threading
import uuid
from typing import Any, Optional

logger = logging.getLogger(__name__)


class MCPClientError(Exception):
    """Raised when an MCP operation fails."""


class MCPClient:
    """Connect to a single MCP Server over stdio.

    Usage::

        client = MCPClient("filesystem", ["npx", "-y", "@modelcontextprotocol/server-filesystem", "/tmp"])
        client.connect()
        tools = client.list_tools()
        result = client.call_tool("read_file", {"path": "/tmp/hello.txt"})
        client.disconnect()
    """

    def __init__(self, name: str, command: list[str], env: dict | None = None):
        self.name = name
        self.command = command
        self.env = env
        self._process: Optional[subprocess.Popen] = None
        self._lock = threading.Lock()
        self._request_id = 0
        self._initialized = False
        self._server_info: dict = {}

    # ── lifecycle ──────────────────────────────────────────────

    def connect(self, timeout: float = 15.0) -> None:
        """Start the MCP Server process and perform the initialize handshake."""
        if self._process is not None:
            return

        logger.info("MCP %s: starting %s", self.name, " ".join(self.command))
        try:
            self._process = subprocess.Popen(
                self.command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                bufsize=1,
            )
        except FileNotFoundError as exc:
            raise MCPClientError(f"MCP {self.name}: command not found: {self.command[0]}") from exc

        try:
            init_response = self._send_request("initialize", {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "AuraSaaS", "version": "0.2.0"},
            })
            self._server_info = init_response.get("result", init_response)
            self._initialized = True
            logger.info("MCP %s: connected — server=%s", self.name, self._server_info.get("serverInfo", {}).get("name", "unknown"))
        except Exception:
            self.disconnect()
            raise

    def disconnect(self) -> None:
        """Terminate the MCP Server process."""
        if self._process is None:
            return
        try:
            self._process.stdin.close()
            self._process.stdout.close()
            self._process.terminate()
            self._process.wait(timeout=5)
        except Exception:
            try:
                self._process.kill()
            except Exception:
                pass
        self._process = None
        self._initialized = False
        logger.info("MCP %s: disconnected", self.name)

    @property
    def is_connected(self) -> bool:
        return self._initialized and self._process is not None and self._process.poll() is None

    # ── tool operations ────────────────────────────────────────

    def list_tools(self) -> list[dict]:
        """Return the MCP Server's tool list.

        Each tool dict has: ``name``, ``description``, ``inputSchema`` (JSON Schema).
        """
        response = self._send_request("tools/list", {})
        return response.get("result", {}).get("tools", [])

    def call_tool(self, name: str, arguments: dict) -> dict:
        """Call a tool on the MCP Server and return its result."""
        response = self._send_request("tools/call", {"name": name, "arguments": arguments})
        result = response.get("result", response)
        content = result.get("content", [])
        # Extract text from content blocks
        texts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                texts.append(block.get("text", ""))
        return {
            "success": True,
            "data": "\n".join(texts) if texts else json.dumps(result, ensure_ascii=False),
            "raw": result,
        }

    # ── JSON-RPC core ──────────────────────────────────────────

    def _next_id(self) -> int:
        with self._lock:
            self._request_id += 1
            return self._request_id

    def _send_request(self, method: str, params: dict) -> dict:
        """Send a JSON-RPC request and return the parsed response."""
        if self._process is None:
            raise MCPClientError(f"MCP {self.name}: not connected")

        request_id = self._next_id()
        request = json.dumps({
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params,
        }, ensure_ascii=False)

        with self._lock:
            try:
                self._process.stdin.write(request + "\n")
                self._process.stdin.flush()
            except (BrokenPipeError, OSError) as exc:
                raise MCPClientError(f"MCP {self.name}: write failed — server may have crashed") from exc

            try:
                line = self._process.stdout.readline()
            except Exception as exc:
                raise MCPClientError(f"MCP {self.name}: read failed") from exc

            if not line:
                # Check stderr for error info
                stderr_info = ""
                try:
                    import select
                    if select.select([self._process.stderr], [], [], 0.1)[0]:
                        stderr_info = self._process.stderr.readline() or ""
                except Exception:
                    pass
                raise MCPClientError(f"MCP {self.name}: server closed connection. stderr: {stderr_info.strip()}")

        try:
            parsed = json.loads(line)
        except json.JSONDecodeError as exc:
            raise MCPClientError(f"MCP {self.name}: invalid JSON response: {line[:200]}") from exc

        if "error" in parsed:
            err = parsed["error"]
            raise MCPClientError(f"MCP {self.name}: {err.get('message', str(err))}")

        return parsed


# ── In-memory MCP Server (fallback when real MCP Server unavailable) ─────

class InMemoryMCPServer:
    """Fake MCP Server with pre-defined tools — used when no real MCP Server is configured.

    This allows the MCP adapter and tool registration flow to work
    without requiring ``npx`` or the official MCP server packages.
    """

    def __init__(self, name: str, tools: list[dict]):
        self.name = name
        self._tools = tools

    def list_tools(self) -> list[dict]:
        return self._tools

    def call_tool(self, name: str, arguments: dict) -> dict:
        return {
            "success": True,
            "data": f"[{self.name}] Tool '{name}' called with {json.dumps(arguments, ensure_ascii=False)}. "
                    "This is an in-memory fallback — connect a real MCP Server for live execution.",
        }

    def disconnect(self) -> None:
        pass

    @property
    def is_connected(self) -> bool:
        return True


# ── Pre-built in-memory MCP tools ─────────────────────────────

FILESYSTEM_MCP_TOOLS = [
    {
        "name": "read_file",
        "description": "Read the contents of a file",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to the file to read"},
            },
            "required": ["path"],
        },
    },
    {
        "name": "write_file",
        "description": "Create or overwrite a file",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to the file to write"},
                "content": {"type": "string", "description": "Content to write"},
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "list_directory",
        "description": "List files and directories in a given path",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Directory path to list"},
            },
            "required": ["path"],
        },
    },
    {
        "name": "search_files",
        "description": "Search for files matching a pattern in a directory tree",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Root directory to search"},
                "pattern": {"type": "string", "description": "Glob pattern, e.g. *.py"},
            },
            "required": ["path", "pattern"],
        },
    },
]

SQLITE_MCP_TOOLS = [
    {
        "name": "query",
        "description": "Execute a read-only SQL query against the SQLite database",
        "inputSchema": {
            "type": "object",
            "properties": {
                "sql": {"type": "string", "description": "SELECT query to execute"},
            },
            "required": ["sql"],
        },
    },
    {
        "name": "list_tables",
        "description": "List all tables in the SQLite database",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "describe_table",
        "description": "Show the schema of a specific table",
        "inputSchema": {
            "type": "object",
            "properties": {
                "table_name": {"type": "string", "description": "Name of the table to describe"},
            },
            "required": ["table_name"],
        },
    },
]


def create_inmemory_mcp(name: str) -> InMemoryMCPServer:
    """Create an in-memory MCP server with pre-defined tools for demo."""
    tools_map = {
        "filesystem": FILESYSTEM_MCP_TOOLS,
        "sqlite": SQLITE_MCP_TOOLS,
    }
    tools = tools_map.get(name, FILESYSTEM_MCP_TOOLS)
    return InMemoryMCPServer(name, tools)
