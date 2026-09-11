"""A minimal but genuine MCP (Model Context Protocol) implementation.

JSON-RPC 2.0 over stdio, supporting the handshake and tool surface that matter
for this capstone:

    initialize            -> server capabilities + protocol version
    notifications/initialized
    tools/list            -> tool descriptors with JSON Schema
    tools/call            -> execute a tool, return content blocks
    ping                  -> liveness

No third-party dependency, so trainees can read the wire format and test it
directly with a pipe. The servers here are also usable from any MCP host
(Claude Desktop, an IDE) by pointing it at `python -m app.mcpsvc.<server>`.
"""
from __future__ import annotations

import json
import sys
import traceback
from typing import Any, Callable

PROTOCOL_VERSION = "2024-11-05"

# JSON-RPC error codes
PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603


class MCPServer:
    """A tiny MCP server. Register tools, then `serve_stdio()`."""

    def __init__(self, name: str, version: str = "1.0.0", instructions: str = ""):
        self.name = name
        self.version = version
        self.instructions = instructions
        self.tools: dict[str, dict[str, Any]] = {}
        self.handlers: dict[str, Callable[..., Any]] = {}
        self._initialized = False

    def add_tool(self, name: str, description: str, input_schema: dict, handler: Callable[..., Any]) -> None:
        self.tools[name] = {"name": name, "description": description, "inputSchema": input_schema}
        self.handlers[name] = handler

    # -- request handling ------------------------------------------------
    def handle(self, request: dict[str, Any]) -> dict[str, Any] | None:
        rid = request.get("id")
        method = request.get("method")
        params = request.get("params") or {}

        if request.get("jsonrpc") != "2.0":
            return self._error(rid, INVALID_REQUEST, "jsonrpc must be '2.0'")

        # Notifications carry no id and get no response.
        is_notification = "id" not in request

        try:
            if method == "initialize":
                self._initialized = True
                return self._ok(rid, {
                    "protocolVersion": PROTOCOL_VERSION,
                    "capabilities": {"tools": {"listChanged": False}},
                    "serverInfo": {"name": self.name, "version": self.version},
                    "instructions": self.instructions,
                })
            if method in ("notifications/initialized", "initialized"):
                self._initialized = True
                return None
            if method == "ping":
                return self._ok(rid, {})
            if method == "tools/list":
                return self._ok(rid, {"tools": list(self.tools.values())})
            if method == "tools/call":
                return self._call_tool(rid, params)
            if is_notification:
                return None
            return self._error(rid, METHOD_NOT_FOUND, f"Unknown method '{method}'")
        except Exception as exc:  # noqa: BLE001
            if is_notification:
                return None
            return self._error(rid, INTERNAL_ERROR, f"{type(exc).__name__}: {exc}",
                               {"traceback": traceback.format_exc()[-800:]})

    def _call_tool(self, rid, params: dict[str, Any]) -> dict[str, Any]:
        name = params.get("name")
        args = params.get("arguments")
        if not name:
            return self._error(rid, INVALID_PARAMS, "'name' is required")
        if name not in self.handlers:
            return self._error(rid, INVALID_PARAMS, f"Unknown tool '{name}'")
        if args is None:
            args = {}
        if not isinstance(args, dict):
            return self._error(rid, INVALID_PARAMS, "'arguments' must be an object")
        try:
            result = self.handlers[name](**args)
            payload = json.dumps(result, default=str, indent=2)
            return self._ok(rid, {
                "content": [{"type": "text", "text": payload}],
                "isError": bool(isinstance(result, dict) and result.get("ok") is False),
            })
        except Exception as exc:  # noqa: BLE001 - MCP reports tool failure in-band
            return self._ok(rid, {
                "content": [{"type": "text",
                             "text": json.dumps({"ok": False,
                                                 "error": {"code": type(exc).__name__, "message": str(exc)}})}],
                "isError": True,
            })

    @staticmethod
    def _ok(rid, result) -> dict[str, Any]:
        return {"jsonrpc": "2.0", "id": rid, "result": result}

    @staticmethod
    def _error(rid, code: int, message: str, data: Any = None) -> dict[str, Any]:
        err: dict[str, Any] = {"code": code, "message": message}
        if data is not None:
            err["data"] = data
        return {"jsonrpc": "2.0", "id": rid, "error": err}

    # -- transport -------------------------------------------------------
    def serve_stdio(self) -> None:
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                request = json.loads(line)
            except json.JSONDecodeError as exc:
                sys.stdout.write(json.dumps(self._error(None, PARSE_ERROR, str(exc))) + "\n")
                sys.stdout.flush()
                continue
            response = self.handle(request)
            if response is not None:
                sys.stdout.write(json.dumps(response, default=str) + "\n")
                sys.stdout.flush()
