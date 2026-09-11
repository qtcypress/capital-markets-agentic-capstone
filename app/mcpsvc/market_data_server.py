"""MCP server #1 — Market Data.

Owns everything that touches a live external API: quotes, option chains,
futures and FX. Run standalone with:  python -m app.mcpsvc.market_data_server
"""
from __future__ import annotations

from ..agents.tools import REGISTRY, execute_tool
from .protocol import MCPServer

TOOLS = ["get_quote", "get_option_chain", "get_futures", "get_fx_rate", "get_contract_spec"]

INSTRUCTIONS = (
    "Market data server for Indian equity derivatives. Every response carries a "
    "_provenance block stating whether the data is live, a recorded snapshot, or "
    "synthetic. Always surface that provenance to the user."
)


def build_server() -> MCPServer:
    server = MCPServer("qtcap-market-data", "1.0.0", INSTRUCTIONS)
    for name in TOOLS:
        t = REGISTRY[name]
        server.add_tool(name, t.description, t.parameters,
                        lambda _n=name, **kw: execute_tool(_n, kw))
    return server


if __name__ == "__main__":
    build_server().serve_stdio()
