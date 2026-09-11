"""MCP server #2 — Risk & Pricing.

Pure computation: Black-Scholes, Greeks, implied vol, margin and payoff
analytics. No network access, so its results are fully deterministic — which
makes it the easiest MCP server for a trainee to write exact assertions against.
Run standalone with:  python -m app.mcpsvc.risk_server
"""
from __future__ import annotations

from ..agents.tools import REGISTRY, execute_tool
from .protocol import MCPServer

TOOLS = ["price_option", "calc_greeks", "implied_volatility", "calc_margin", "payoff_profile"]

INSTRUCTIONS = (
    "Risk and pricing server. All figures are model outputs for education and "
    "testing, never exchange-accurate margin or executable prices. Margin results "
    "must be presented with their disclaimer intact."
)


def build_server() -> MCPServer:
    server = MCPServer("qtcap-risk", "1.0.0", INSTRUCTIONS)
    for name in TOOLS:
        t = REGISTRY[name]
        server.add_tool(name, t.description, t.parameters,
                        lambda _n=name, **kw: execute_tool(_n, kw))
    return server


if __name__ == "__main__":
    build_server().serve_stdio()
