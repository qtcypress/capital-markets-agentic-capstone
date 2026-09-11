"""MCP client: spawns servers as subprocesses and speaks JSON-RPC over stdio.

Two transports are provided:

  StdioMCPClient  — real subprocess, real pipes. Use this to prove the wire
                    protocol works, and to test timeouts, crashes and restarts.
  InProcessMCPClient — same API, no subprocess. Fast enough to run inside the
                    300-case suite without paying process-spawn cost per test.

Testing both is the point: trainees learn that an integration passing in-process
can still fail across a real transport.
"""
from __future__ import annotations

import json
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..config import ROOT
from .protocol import PROTOCOL_VERSION, MCPServer

SERVER_MODULES = {
    "market_data": "app.mcpsvc.market_data_server",
    "risk": "app.mcpsvc.risk_server",
    "research": "app.mcpsvc.research_server",
}


class MCPClientError(RuntimeError):
    pass


@dataclass
class MCPCallRecord:
    server: str
    tool: str
    arguments: dict[str, Any]
    ok: bool
    duration_ms: int
    result: Any = None
    error: dict[str, Any] | None = None
    transport: str = "in_process"


class BaseMCPClient:
    name = "base"
    transport = "none"

    def initialize(self) -> dict[str, Any]:
        raise NotImplementedError

    def list_tools(self) -> list[dict[str, Any]]:
        raise NotImplementedError

    def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> MCPCallRecord:
        raise NotImplementedError

    def close(self) -> None:
        pass

    # shared decoding of an MCP tools/call result
    def _decode(self, server: str, tool: str, arguments: dict, raw: dict, started: float) -> MCPCallRecord:
        duration = int((time.perf_counter() - started) * 1000)
        if "error" in raw:
            return MCPCallRecord(server, tool, arguments, False, duration,
                                 error=raw["error"], transport=self.transport)
        result = raw.get("result") or {}
        blocks = result.get("content") or []
        text = blocks[0].get("text", "") if blocks else ""
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            payload = {"raw_text": text}
        ok = not result.get("isError", False) and payload.get("ok", True)
        return MCPCallRecord(
            server, tool, arguments, bool(ok), duration,
            result=payload.get("result", payload),
            error=payload.get("error"), transport=self.transport,
        )


class InProcessMCPClient(BaseMCPClient):
    """Talks to an MCPServer object directly — same JSON-RPC envelopes, no pipes."""

    transport = "in_process"

    def __init__(self, server_key: str):
        if server_key not in SERVER_MODULES:
            raise MCPClientError(f"unknown server '{server_key}'")
        self.name = server_key
        module = __import__(SERVER_MODULES[server_key], fromlist=["build_server"])
        self.server: MCPServer = module.build_server()
        self._id = 0
        self.initialized = False

    def _rpc(self, method: str, params: dict | None = None) -> dict:
        self._id += 1
        req = {"jsonrpc": "2.0", "id": self._id, "method": method, "params": params or {}}
        return self.server.handle(req) or {}

    def initialize(self) -> dict[str, Any]:
        resp = self._rpc("initialize", {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {},
            "clientInfo": {"name": "qtcap-orchestrator", "version": "1.0.0"},
        })
        self.initialized = True
        return resp.get("result", {})

    def list_tools(self) -> list[dict[str, Any]]:
        return self._rpc("tools/list").get("result", {}).get("tools", [])

    def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> MCPCallRecord:
        started = time.perf_counter()
        raw = self._rpc("tools/call", {"name": name, "arguments": arguments or {}})
        return self._decode(self.name, name, arguments or {}, raw, started)


class StdioMCPClient(BaseMCPClient):
    """Spawns `python -m <server module>` and speaks JSON-RPC over its pipes."""

    transport = "stdio"

    def __init__(self, server_key: str, timeout_s: float = 30.0, cwd: Path | None = None):
        if server_key not in SERVER_MODULES:
            raise MCPClientError(f"unknown server '{server_key}'")
        self.name = server_key
        self.timeout_s = timeout_s
        self._id = 0
        self._lock = threading.Lock()
        self.proc = subprocess.Popen(
            [sys.executable, "-m", SERVER_MODULES[server_key]],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, bufsize=1, cwd=str(cwd or ROOT),
        )
        self.initialized = False

    def _rpc(self, method: str, params: dict | None = None, notify: bool = False) -> dict:
        if self.proc.poll() is not None:
            raise MCPClientError(f"server '{self.name}' exited with code {self.proc.returncode}")
        with self._lock:
            req: dict[str, Any] = {"jsonrpc": "2.0", "method": method, "params": params or {}}
            if not notify:
                self._id += 1
                req["id"] = self._id
            self.proc.stdin.write(json.dumps(req) + "\n")
            self.proc.stdin.flush()
            if notify:
                return {}
            line = self.proc.stdout.readline()
            if not line:
                stderr = self.proc.stderr.read() if self.proc.stderr else ""
                raise MCPClientError(f"server '{self.name}' closed the pipe. stderr: {stderr[-400:]}")
            return json.loads(line)

    def initialize(self) -> dict[str, Any]:
        resp = self._rpc("initialize", {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {},
            "clientInfo": {"name": "qtcap-orchestrator", "version": "1.0.0"},
        })
        self._rpc("notifications/initialized", notify=True)
        self.initialized = True
        return resp.get("result", {})

    def list_tools(self) -> list[dict[str, Any]]:
        return self._rpc("tools/list").get("result", {}).get("tools", [])

    def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> MCPCallRecord:
        started = time.perf_counter()
        raw = self._rpc("tools/call", {"name": name, "arguments": arguments or {}})
        return self._decode(self.name, name, arguments or {}, raw, started)

    def close(self) -> None:
        try:
            if self.proc.poll() is None:
                self.proc.stdin.close()
                self.proc.wait(timeout=5)
        except Exception:  # noqa: BLE001
            self.proc.kill()


@dataclass
class MCPSession:
    """Holds one client per server and a routing table of tool -> server."""

    transport: str = "in_process"
    clients: dict[str, BaseMCPClient] = field(default_factory=dict)
    routing: dict[str, str] = field(default_factory=dict)
    server_info: dict[str, dict] = field(default_factory=dict)

    @classmethod
    def start(cls, transport: str = "in_process", servers: list[str] | None = None) -> "MCPSession":
        session = cls(transport=transport)
        for key in servers or list(SERVER_MODULES):
            client = StdioMCPClient(key) if transport == "stdio" else InProcessMCPClient(key)
            session.server_info[key] = client.initialize()
            for tool in client.list_tools():
                session.routing[tool["name"]] = key
            session.clients[key] = client
        return session

    def call(self, tool: str, arguments: dict[str, Any] | None = None) -> MCPCallRecord:
        server = self.routing.get(tool)
        if server is None:
            return MCPCallRecord("<none>", tool, arguments or {}, False, 0,
                                 error={"code": "tool_not_found",
                                        "message": f"No MCP server exposes '{tool}'. "
                                                   f"Available: {sorted(self.routing)}"},
                                 transport=self.transport)
        return self.clients[server].call_tool(tool, arguments)

    def all_tools(self) -> list[dict[str, Any]]:
        out = []
        for key, client in self.clients.items():
            for t in client.list_tools():
                out.append({**t, "_server": key})
        return out

    def close(self) -> None:
        for client in self.clients.values():
            client.close()
