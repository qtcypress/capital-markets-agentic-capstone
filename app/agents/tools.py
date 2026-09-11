"""Tool registry shared by the single agent and the MCP servers.

Each tool carries a JSON Schema, a risk tier, and an explicit argument
validator. The validator matters: a large share of the blue-team suite targets
*tool contract* behaviour (wrong types, missing arguments, out-of-range values)
rather than model behaviour, and that is where a manual tester's existing
instincts transfer most directly.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable

from ..config import get_config
from ..market import (
    CONTRACT_SPECS,
    analyse_payoff,
    black_scholes,
    build_strategy,
    calculate_margin,
    get_contract_spec,
    get_futures,
    get_fx_rate,
    get_option_chain,
    get_quote,
    implied_volatility,
    max_pain,
    normalise_symbol,
    pcr_interpretation,
)
from ..market.sources import IST, MarketDataError

RiskTier = str  # "read" | "compute" | "sensitive"


class ToolError(RuntimeError):
    """Raised for a bad call; surfaced to the agent as a structured error."""

    def __init__(self, message: str, code: str = "invalid_argument"):
        super().__init__(message)
        self.code = code


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict[str, Any]
    handler: Callable[..., dict[str, Any]]
    risk: RiskTier = "read"
    domain: str = "market"

    def schema(self) -> dict[str, Any]:
        return {"name": self.name, "description": self.description, "parameters": self.parameters}


REGISTRY: dict[str, Tool] = {}


def tool(name: str, description: str, parameters: dict, risk: RiskTier = "read", domain: str = "market"):
    def wrap(fn):
        REGISTRY[name] = Tool(name, description, parameters, fn, risk, domain)
        return fn

    return wrap


# ---------------------------------------------------------------------------
# Argument validation helpers
# ---------------------------------------------------------------------------
def _req_symbol(args: dict, key: str = "symbol") -> str:
    raw = args.get(key)
    if raw is None or not str(raw).strip():
        raise ToolError(f"'{key}' is required", "missing_argument")
    if not isinstance(raw, str):
        raise ToolError(f"'{key}' must be a string, got {type(raw).__name__}", "type_error")
    sym = normalise_symbol(raw)
    if not sym.isalnum():
        raise ToolError(f"'{key}' contains invalid characters: {raw!r}", "invalid_argument")
    if len(sym) > 20:
        raise ToolError(f"'{key}' is too long", "invalid_argument")
    return sym


def _num(args: dict, key: str, *, required: bool = True, default: float | None = None,
         minimum: float | None = None, maximum: float | None = None) -> float | None:
    if key not in args or args[key] is None:
        if required:
            raise ToolError(f"'{key}' is required", "missing_argument")
        return default
    val = args[key]
    if isinstance(val, bool) or not isinstance(val, (int, float, str)):
        raise ToolError(f"'{key}' must be a number, got {type(val).__name__}", "type_error")
    try:
        val = float(val)
    except (TypeError, ValueError):
        raise ToolError(f"'{key}' must be a number, got {args[key]!r}", "type_error") from None
    if val != val or val in (float("inf"), float("-inf")):
        raise ToolError(f"'{key}' must be a finite number", "invalid_argument")
    if minimum is not None and val < minimum:
        raise ToolError(f"'{key}' must be >= {minimum}, got {val}", "out_of_range")
    if maximum is not None and val > maximum:
        raise ToolError(f"'{key}' must be <= {maximum}, got {val}", "out_of_range")
    return val


def _int(args: dict, key: str, *, required: bool = True, default: int | None = None,
         minimum: int | None = None, maximum: int | None = None) -> int | None:
    val = _num(args, key, required=required,
               default=None if default is None else float(default),
               minimum=minimum, maximum=maximum)
    if val is None:
        return default
    if abs(val - round(val)) > 1e-9:
        raise ToolError(f"'{key}' must be a whole number, got {val}", "type_error")
    return int(round(val))


def _years_to_expiry(expiry: str | None, default_days: int = 30) -> tuple[float, int]:
    if not expiry:
        return default_days / 365, default_days
    for fmt in ("%Y-%m-%d", "%d-%b-%Y", "%d/%m/%Y"):
        try:
            d = datetime.strptime(expiry, fmt).replace(tzinfo=IST)
        except ValueError:
            continue
        days = (d.date() - datetime.now(IST).date()).days
        if days < 0:
            raise ToolError(f"expiry {expiry} is in the past", "out_of_range")
        return max(days, 1) / 365, max(days, 1)
    raise ToolError(f"expiry '{expiry}' is not a recognised date (use YYYY-MM-DD)", "invalid_argument")


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------
@tool(
    "get_quote",
    "Get the latest price for an NSE index or stock, including change, day range and lot size.",
    {
        "type": "object",
        "properties": {"symbol": {"type": "string", "description": "NSE symbol, e.g. NIFTY, BANKNIFTY, RELIANCE"}},
        "required": ["symbol"],
    },
)
def t_get_quote(**args) -> dict[str, Any]:
    sym = _req_symbol(args)
    payload = get_quote(sym)
    return {**payload.data, "_provenance": {
        "source": payload.source, "provider": payload.provider,
        "as_of": payload.as_of, "stale": payload.stale, "warnings": payload.warnings}}


@tool(
    "get_option_chain",
    "Get the option chain for an index or stock: strikes, LTP, open interest, IV and put-call ratio.",
    {
        "type": "object",
        "properties": {
            "symbol": {"type": "string", "description": "NIFTY, BANKNIFTY, FINNIFTY or an F&O stock"},
            "expiry": {"type": "string", "description": "Optional expiry, e.g. 2026-09-24"},
            "strikes_around_atm": {"type": "integer", "description": "How many strikes each side of ATM (default 5, max 25)"},
        },
        "required": ["symbol"],
    },
)
def t_get_option_chain(**args) -> dict[str, Any]:
    sym = _req_symbol(args)
    window = _int(args, "strikes_around_atm", required=False, default=5, minimum=1, maximum=25)
    payload = get_option_chain(sym, args.get("expiry"))
    data = dict(payload.data)
    rows = data.get("strikes") or []
    spot = data.get("underlying_value")
    if spot and rows:
        rows = sorted(rows, key=lambda r: abs((r.get("strike") or 0) - spot))[: window * 2 + 1]
        rows.sort(key=lambda r: r.get("strike") or 0)
        data["strikes"] = rows
        data["window_applied"] = window
    data["pcr_reading"] = pcr_interpretation(data.get("pcr"))
    data["max_pain"] = max_pain(data.get("strikes") or [])
    return {**data, "_provenance": {
        "source": payload.source, "provider": payload.provider,
        "as_of": payload.as_of, "stale": payload.stale, "warnings": payload.warnings}}


@tool(
    "get_futures",
    "Get the futures view for a symbol: spot, model fair value, basis, days to expiry and contract value.",
    {"type": "object", "properties": {"symbol": {"type": "string"}}, "required": ["symbol"]},
)
def t_get_futures(**args) -> dict[str, Any]:
    sym = _req_symbol(args)
    payload = get_futures(sym)
    return {**payload.data, "_provenance": {
        "source": payload.source, "provider": payload.provider,
        "as_of": payload.as_of, "stale": payload.stale, "warnings": payload.warnings}}


@tool(
    "get_fx_rate",
    "Get a reference foreign-exchange rate, e.g. USD/INR, from the ECB reference feed.",
    {
        "type": "object",
        "properties": {"base": {"type": "string", "default": "USD"}, "quote": {"type": "string", "default": "INR"}},
        "required": [],
    },
)
def t_get_fx_rate(**args) -> dict[str, Any]:
    base = (args.get("base") or "USD").upper()
    quote = (args.get("quote") or "INR").upper()
    for code in (base, quote):
        if not (code.isalpha() and len(code) == 3):
            raise ToolError(f"currency code '{code}' must be three letters", "invalid_argument")
    payload = get_fx_rate(base, quote)
    return {**payload.data, "_provenance": {
        "source": payload.source, "provider": payload.provider,
        "as_of": payload.as_of, "stale": payload.stale, "warnings": payload.warnings}}


@tool(
    "price_option",
    "Price a European option with Black-Scholes and return its theoretical value.",
    {
        "type": "object",
        "properties": {
            "symbol": {"type": "string"},
            "strike": {"type": "number"},
            "option_type": {"type": "string", "enum": ["call", "put"]},
            "expiry": {"type": "string", "description": "YYYY-MM-DD; defaults to 30 days out"},
            "volatility": {"type": "number", "description": "Annualised vol as a decimal, e.g. 0.14"},
            "spot": {"type": "number", "description": "Override spot; otherwise fetched live"},
        },
        "required": ["symbol", "strike"],
    },
    risk="compute",
)
def t_price_option(**args) -> dict[str, Any]:
    sym = _req_symbol(args)
    strike = _num(args, "strike", minimum=0.01, maximum=10_000_000)
    opt_type = (args.get("option_type") or "call").lower()
    if opt_type not in ("call", "put"):
        raise ToolError("option_type must be 'call' or 'put'", "invalid_argument")
    sigma = _num(args, "volatility", required=False, default=0.14, minimum=0.0001, maximum=5.0)
    t, days = _years_to_expiry(args.get("expiry"))
    spot = _num(args, "spot", required=False)
    provenance = {"source": "user_supplied", "provider": "override"}
    if spot is None:
        q = get_quote(sym)
        spot = q.data["last_price"]
        provenance = {"source": q.source, "provider": q.provider, "as_of": q.as_of, "stale": q.stale}
    r = get_config().market.risk_free_rate
    greeks = black_scholes(spot, strike, t, r, sigma, opt_type)
    return {
        "symbol": sym, "strike": strike, "option_type": opt_type, "spot": spot,
        "days_to_expiry": days, "volatility": sigma, "risk_free_rate": r,
        "moneyness": "ITM" if ((opt_type == "call" and spot > strike) or (opt_type == "put" and spot < strike))
        else "OTM" if ((opt_type == "call" and spot < strike) or (opt_type == "put" and spot > strike)) else "ATM",
        **greeks,
        "model": "Black-Scholes-Merton (European, no dividends)",
        "_provenance": provenance,
    }


@tool(
    "calc_greeks",
    "Calculate the full Greek set (delta, gamma, theta, vega, rho) for an option position.",
    {
        "type": "object",
        "properties": {
            "symbol": {"type": "string"},
            "strike": {"type": "number"},
            "option_type": {"type": "string", "enum": ["call", "put"]},
            "expiry": {"type": "string"},
            "volatility": {"type": "number"},
            "lots": {"type": "integer", "description": "Position size in lots for scaled Greeks"},
        },
        "required": ["symbol", "strike"],
    },
    risk="compute",
)
def t_calc_greeks(**args) -> dict[str, Any]:
    base = t_price_option(**args)
    lots = _int(args, "lots", required=False, default=1, minimum=1, maximum=10000)
    lot_size = CONTRACT_SPECS.get(base["symbol"], {}).get("lot_size", 1)
    qty = lots * lot_size
    return {
        **base,
        "lots": lots, "lot_size": lot_size, "quantity": qty,
        "position_greeks": {
            "delta": round(base["delta"] * qty, 4),
            "gamma": round(base["gamma"] * qty, 6),
            "vega": round(base["vega"] * qty, 4),
            "theta": round(base["theta"] * qty, 4),
            "rho": round(base["rho"] * qty, 4),
        },
        "interpretation": {
            "delta": f"Position gains about {round(base['delta'] * qty, 2)} rupees per 1-point move in the underlying.",
            "theta": f"Position loses about {abs(round(base['theta'] * qty, 2))} rupees per calendar day, all else equal."
            if base["theta"] < 0 else f"Position gains about {round(base['theta'] * qty, 2)} rupees per calendar day.",
            "vega": f"Position changes by about {round(base['vega'] * qty, 2)} rupees per 1 volatility point.",
        },
    }


@tool(
    "implied_volatility",
    "Back out implied volatility from a traded option premium.",
    {
        "type": "object",
        "properties": {
            "symbol": {"type": "string"}, "strike": {"type": "number"},
            "market_price": {"type": "number"}, "option_type": {"type": "string", "enum": ["call", "put"]},
            "expiry": {"type": "string"}, "spot": {"type": "number"},
        },
        "required": ["symbol", "strike", "market_price"],
    },
    risk="compute",
)
def t_implied_vol(**args) -> dict[str, Any]:
    sym = _req_symbol(args)
    strike = _num(args, "strike", minimum=0.01)
    price = _num(args, "market_price", minimum=0.0001)
    opt_type = (args.get("option_type") or "call").lower()
    if opt_type not in ("call", "put"):
        raise ToolError("option_type must be 'call' or 'put'", "invalid_argument")
    t, days = _years_to_expiry(args.get("expiry"))
    spot = _num(args, "spot", required=False)
    if spot is None:
        spot = get_quote(sym).data["last_price"]
    res = implied_volatility(price, spot, strike, t, get_config().market.risk_free_rate, opt_type)
    return {"symbol": sym, "strike": strike, "option_type": opt_type, "spot": spot,
            "market_price": price, "days_to_expiry": days, **res}


@tool(
    "calc_margin",
    "Estimate the indicative SPAN + exposure margin for a futures or options position.",
    {
        "type": "object",
        "properties": {
            "symbol": {"type": "string"},
            "position": {"type": "string", "enum": ["futures_long", "futures_short", "option_buy", "option_sell"]},
            "lots": {"type": "integer"},
            "premium": {"type": "number", "description": "Option premium per unit, for option positions"},
            "spot": {"type": "number"},
        },
        "required": ["symbol"],
    },
    risk="compute",
)
def t_calc_margin(**args) -> dict[str, Any]:
    sym = _req_symbol(args)
    position = (args.get("position") or "futures_long").lower()
    lots = _int(args, "lots", required=False, default=1, minimum=1, maximum=10000)
    premium = _num(args, "premium", required=False, default=0.0, minimum=0.0) or 0.0
    spot = _num(args, "spot", required=False)
    provenance = {"source": "user_supplied", "provider": "override"}
    if spot is None:
        q = get_quote(sym)
        spot = q.data["last_price"]
        provenance = {"source": q.source, "provider": q.provider, "as_of": q.as_of, "stale": q.stale}
    lot_size = CONTRACT_SPECS.get(sym, {}).get("lot_size")
    if not lot_size:
        raise ToolError(f"{sym} is not in the F&O contract master; margin cannot be computed", "unknown_symbol")
    try:
        result = calculate_margin(sym, spot, lot_size, lots, position, premium)
    except ValueError as exc:
        raise ToolError(str(exc), "invalid_argument") from exc
    return {**result, "spot": spot, "_provenance": provenance}


@tool(
    "payoff_profile",
    "Build the payoff profile for a named option strategy: breakevens, max profit and max loss.",
    {
        "type": "object",
        "properties": {
            "symbol": {"type": "string"},
            "strategy": {"type": "string", "description": "long_straddle, bull_call_spread, iron_condor, ..."},
            "volatility": {"type": "number"},
            "expiry": {"type": "string"},
            "spot": {"type": "number"},
        },
        "required": ["symbol", "strategy"],
    },
    risk="compute",
)
def t_payoff(**args) -> dict[str, Any]:
    sym = _req_symbol(args)
    strategy = str(args.get("strategy") or "").strip()
    if not strategy:
        raise ToolError("'strategy' is required", "missing_argument")
    sigma = _num(args, "volatility", required=False, default=0.14, minimum=0.0001, maximum=5.0)
    t, days = _years_to_expiry(args.get("expiry"))
    spot = _num(args, "spot", required=False)
    if spot is None:
        spot = get_quote(sym).data["last_price"]
    spec = CONTRACT_SPECS.get(sym, {"strike_step": 50, "lot_size": 1})
    try:
        result = build_strategy(strategy, spot, spec["strike_step"], t, get_config().market.risk_free_rate,
                                sigma, spec.get("lot_size", 1))
    except ValueError as exc:
        raise ToolError(str(exc), "invalid_argument") from exc
    result["symbol"] = sym
    result["days_to_expiry"] = days
    result["payoff_curve"] = result["payoff_curve"][::4]  # thin for transport
    return result


@tool(
    "get_contract_spec",
    "Look up the contract specification for an F&O symbol: lot size, tick, strike step, expiry day.",
    {"type": "object", "properties": {"symbol": {"type": "string"}}, "required": ["symbol"]},
)
def t_contract_spec(**args) -> dict[str, Any]:
    sym = _req_symbol(args)
    try:
        return get_contract_spec(sym)
    except MarketDataError as exc:
        raise ToolError(str(exc), "unknown_symbol") from exc


@tool(
    "search_knowledge_base",
    "Search the capital-markets reference corpus for concepts, rules, definitions and procedures.",
    {
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "top_k": {"type": "integer", "description": "How many passages to return (default 3, max 8)"},
        },
        "required": ["query"],
    },
    domain="research",
)
def t_search_kb(**args) -> dict[str, Any]:
    from ..rag.store import get_store

    q = args.get("query")
    if not q or not str(q).strip():
        raise ToolError("'query' is required", "missing_argument")
    if len(str(q)) > 2000:
        raise ToolError("'query' exceeds 2000 characters", "out_of_range")
    top_k = _int(args, "top_k", required=False, default=3, minimum=1, maximum=8)
    hits = get_store().search(str(q), top_k=top_k, min_score=0.05)
    return {
        "query": q,
        "results": [
            {"doc_id": h["chunk"].doc_id, "section": h["chunk"].section, "score": h["score"],
             "authority": h["chunk"].authority, "excerpt": h["chunk"].text[:900]}
            for h in hits
        ],
        "result_count": len(hits),
    }


def get_tool_schemas(names: list[str] | None = None) -> list[dict[str, Any]]:
    tools = REGISTRY.values() if names is None else [REGISTRY[n] for n in names if n in REGISTRY]
    return [t.schema() for t in tools]


def execute_tool(name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
    """Execute a tool by name, returning a uniform envelope (never raising)."""
    started = time.perf_counter()
    arguments = arguments or {}
    if name not in REGISTRY:
        return {"ok": False, "tool": name, "error": {"code": "unknown_tool",
                "message": f"No such tool '{name}'. Available: {sorted(REGISTRY)}"},
                "duration_ms": 0}
    if not isinstance(arguments, dict):
        return {"ok": False, "tool": name, "error": {"code": "type_error",
                "message": "arguments must be an object"}, "duration_ms": 0}
    try:
        result = REGISTRY[name].handler(**arguments)
        ok, payload, error = True, result, None
    except ToolError as exc:
        ok, payload, error = False, None, {"code": exc.code, "message": str(exc)}
    except MarketDataError as exc:
        ok, payload, error = False, None, {"code": "data_unavailable", "message": str(exc)}
    except TypeError as exc:
        ok, payload, error = False, None, {"code": "invalid_argument", "message": str(exc)}
    except Exception as exc:  # noqa: BLE001 - agent must see a structured failure
        ok, payload, error = False, None, {"code": "internal_error", "message": f"{type(exc).__name__}: {exc}"}
    return {
        "ok": ok, "tool": name, "arguments": arguments, "result": payload, "error": error,
        "risk": REGISTRY[name].risk, "duration_ms": int((time.perf_counter() - started) * 1000),
    }
