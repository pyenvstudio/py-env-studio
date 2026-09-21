"""MCP stdio server for Py Env Studio (stdlib only, no network, no SDK).

Implements the minimal MCP JSON-RPC surface over newline-delimited stdio::

    initialize -> {protocolVersion, capabilities, serverInfo}
    tools/list -> Phase 1 read-only tools
    tools/call -> thin-adapter dispatch
    ping       -> {}

The dispatch layer (``handle_message``) is transport-independent so a
future Streamable HTTP transport can reuse it without redesigning tools.

Logging policy: never write to stdout (protocol channel). All diagnostics
go to stderr / logging.
"""

from __future__ import annotations

import json
import logging
import sys

from .config import PROTOCOL_VERSION, SERVER_NAME, load_mcp_settings
from .tools import TOOL_DEFINITIONS, dispatch, tool_schemas

logger = logging.getLogger("pes.mcp")

READ_ONLY_TOOL_NAMES = tuple(entry["name"] for entry in TOOL_DEFINITIONS)


class PesMcpServer(object):
    """Transport-independent JSON-RPC dispatcher + stdio runner."""

    def __init__(self, server_name=None):
        try:
            settings = load_mcp_settings()
        except Exception:
            settings = {}
        self.server_name = server_name or settings.get("server_name") or SERVER_NAME
        self._initialized = False

    # -- pure dispatch (reused by any future transport) -------------------
    def handle_message(self, message):
        # type: (dict) -> dict | None
        if not isinstance(message, dict):
            return self._error(None, -32600, "Invalid Request: expected object.")
        msg_id = message.get("id")
        method = message.get("method")
        params = message.get("params") or {}
        if not isinstance(params, dict):
            return self._error(msg_id, -32602, "Invalid params: expected object.")

        if method == "initialize":
            self._initialized = True
            return self._ok(
                msg_id,
                {
                    "protocolVersion": PROTOCOL_VERSION,
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": self.server_name, "version": self._version()},
                },
            )
        if method in ("notifications/initialized", "notifications/cancelled"):
            return None
        if method == "ping":
            return self._ok(msg_id, {})
        if method == "tools/list":
            return self._ok(msg_id, {"tools": tool_schemas()})
        if method == "tools/call":
            return self._handle_tools_call(msg_id, params)
        return self._error(msg_id, -32601, "Method not found: {}".format(method))

    def _handle_tools_call(self, msg_id, params):
        tool_name = params.get("name")
        arguments = params.get("arguments") or {}
        if not tool_name:
            return self._error(msg_id, -32602, "Invalid params: 'name' is required.")
        if not isinstance(arguments, dict):
            return self._error(msg_id, -32602, "Invalid params: 'arguments' must be an object.")
        envelope = dispatch(tool_name, arguments)
        if envelope is None:
            return self._error(msg_id, -32601, "Unknown tool: {}".format(tool_name))
        text = json.dumps(envelope, default=str)
        # MCP content envelope; structuredContent carries the same payload
        # for clients that prefer typed data over text.
        return self._ok(
            msg_id,
            {
                "content": [{"type": "text", "text": text}],
                "structuredContent": envelope,
                "isError": not envelope.get("success", False),
            },
        )

    # -- stdio transport ---------------------------------------------------
    def serve_stdio(self, stdin=None, stdout=None):
        stdin = stdin or sys.stdin
        stdout = stdout or sys.stdout
        for line in stdin:
            if not line.strip():
                continue
            try:
                message = json.loads(line)
            except ValueError:
                stdout.write(json.dumps(self._error(None, -32700, "Parse error.")) + "\n")
                stdout.flush()
                continue
            try:
                response = self.handle_message(message)
            except Exception as exc:  # pragma: no cover - defensive
                logger.exception("MCP dispatch failed: %s", exc)
                response = self._error(message.get("id"), -32603, "Internal error.")
            if response is not None:
                stdout.write(json.dumps(response, default=str) + "\n")
                stdout.flush()

    # -- helpers -----------------------------------------------------------
    @staticmethod
    def _ok(msg_id, result):
        return {"jsonrpc": "2.0", "id": msg_id, "result": result}

    @staticmethod
    def _error(msg_id, code, message):
        return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": code, "message": message}}

    @staticmethod
    def _version():
        try:
            from py_env_studio.core.configuration import AppConfig

            return AppConfig().version
        except Exception:
            return "unknown"


def create_server(server_name=None):
    # type: (...) -> PesMcpServer
    return PesMcpServer(server_name=server_name)


def run_stdio():
    """Entrypoint for ``py-env-studio mcp``: stdio only, logs to stderr."""
    logging.basicConfig(stream=sys.stderr, level=logging.INFO, format="%(levelname)s pes.mcp %(message)s")
    try:
        settings = load_mcp_settings()
    except Exception:
        settings = {"server_name": SERVER_NAME}
    if not settings.get("enabled", True):
        print("MCP server is disabled (config [mcp] enabled=false).", file=sys.stderr)
        return 1
    server = create_server(settings.get("server_name"))
    server.serve_stdio()
    return 0
