"""Derivatives pricing, Greeks, margin and payoff analytics.

This module is deliberately pure and deterministic: given the same inputs it
always returns the same numbers. That makes it the ideal first target for a
manual tester moving into automation — you can write exact-value assertions
here before graduating to the fuzzy assertions needed for LLM output.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Literal

OptionType = Literal["call", "put"]

SQRT_2PI = math.sqrt(2 * math.pi)


def _norm_pdf(x: float) -> float:
    return math.exp(-0.5 * x * x) / SQRT_2PI


def _norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _validate(spot: float, strike: float, t: float, sigma: float) -> None:
    if spot <= 0:
        raise ValueError("spot must be positive")
    if strike <= 0:
        raise ValueError("strike must be positive")
    if t < 0:
        raise ValueError("time to expiry cannot be negative")
    if sigma < 0:
        raise ValueError("volatility cannot be negative")


def black_scholes(
    spot: float,
    strike: float,
    t: float,
    r: float,
    sigma: float,
    option_type: OptionType = "call",
    q: float = 0.0,
) -> dict[str, float]:
    """European option price and full Greek set (Black-Scholes-Merton).

    t is in years, r and q are continuously compounded annual rates, sigma is
    annualised volatility as a decimal (0.14 == 14%).
    """
    _validate(spot, strike, t, sigma)
    option_type = option_type.lower()  # type: ignore[assignment]
    if option_type not in ("call", "put"):
        raise ValueError("option_type must be 'call' or 'put'")

    # Expiry or zero-vol edge case: intrinsic value only.
    if t == 0 or sigma == 0:
        intrinsic = max(spot - strike, 0.0) if option_type == "call" else max(strike - spot, 0.0)
        return {
            "price": round(intrinsic, 4), "delta": float(intrinsic > 0) * (1 if option_type == "call" else -1),
            "gamma": 0.0, "vega": 0.0, "theta": 0.0, "rho": 0.0,
            "d1": 0.0, "d2": 0.0, "intrinsic": round(intrinsic, 4), "time_value": 0.0,
        }

    vol_t = sigma * math.sqrt(t)
    d1 = (math.log(spot / strike) + (r - q + 0.5 * sigma**2) * t) / vol_t
    d2 = d1 - vol_t
    disc_r, disc_q = math.exp(-r * t), math.exp(-q * t)

    if option_type == "call":
        price = spot * disc_q * _norm_cdf(d1) - strike * disc_r * _norm_cdf(d2)
        delta = disc_q * _norm_cdf(d1)
        theta = (
            -(spot * disc_q * _norm_pdf(d1) * sigma) / (2 * math.sqrt(t))
            - r * strike * disc_r * _norm_cdf(d2)
            + q * spot * disc_q * _norm_cdf(d1)
        )
        rho = strike * t * disc_r * _norm_cdf(d2)
    else:
        price = strike * disc_r * _norm_cdf(-d2) - spot * disc_q * _norm_cdf(-d1)
        delta = -disc_q * _norm_cdf(-d1)
        theta = (
            -(spot * disc_q * _norm_pdf(d1) * sigma) / (2 * math.sqrt(t))
            + r * strike * disc_r * _norm_cdf(-d2)
            - q * spot * disc_q * _norm_cdf(-d1)
        )
        rho = -strike * t * disc_r * _norm_cdf(-d2)

    gamma = (disc_q * _norm_pdf(d1)) / (spot * vol_t)
    vega = spot * disc_q * _norm_pdf(d1) * math.sqrt(t)
    intrinsic = max(spot - strike, 0.0) if option_type == "call" else max(strike - spot, 0.0)

    return {
        "price": round(price, 4),
        "delta": round(delta, 6),
        "gamma": round(gamma, 8),
        "vega": round(vega / 100, 6),      # per 1 vol point
        "theta": round(theta / 365, 6),    # per calendar day
        "rho": round(rho / 100, 6),        # per 1% rate move
        "d1": round(d1, 6),
        "d2": round(d2, 6),
        "intrinsic": round(intrinsic, 4),
        "time_value": round(price - intrinsic, 4),
    }


def implied_volatility(
    market_price: float,
    spot: float,
    strike: float,
    t: float,
    r: float,
    option_type: OptionType = "call",
    q: float = 0.0,
    tol: float = 1e-6,
    max_iter: int = 100,
) -> dict[str, Any]:
    """Solve for implied vol by bisection (robust; no derivative blow-ups)."""
    if market_price <= 0:
        raise ValueError("market price must be positive")
    intrinsic = max(spot - strike, 0.0) if option_type == "call" else max(strike - spot, 0.0)
    if market_price < intrinsic - 1e-9:
        return {"implied_vol": None, "converged": False,
                "reason": "market price is below intrinsic value — arbitrage or bad input"}
    lo, hi = 1e-6, 5.0
    if black_scholes(spot, strike, t, r, hi, option_type, q)["price"] < market_price:
        return {"implied_vol": None, "converged": False,
                "reason": "price exceeds the model maximum at 500% volatility"}
    iters = 0
    for iters in range(1, max_iter + 1):
        mid = (lo + hi) / 2
        px = black_scholes(spot, strike, t, r, mid, option_type, q)["price"]
        if abs(px - market_price) < tol:
            break
        if px > market_price:
            hi = mid
        else:
            lo = mid
    vol = (lo + hi) / 2
    return {
        "implied_vol": round(vol, 6),
        "implied_vol_pct": round(vol * 100, 2),
        "converged": True,
        "iterations": iters,
    }


# ---------------------------------------------------------------------------
# Margin
# ---------------------------------------------------------------------------
@dataclass
class MarginResult:
    symbol: str
    position: str
    lots: int
    lot_size: int
    contract_value: float
    span_margin: float
    exposure_margin: float
    total_margin: float
    premium_receivable: float
    methodology: str
    disclaimer: str

    def to_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


def calculate_margin(
    symbol: str,
    spot: float,
    lot_size: int,
    lots: int = 1,
    position: str = "futures_long",
    premium: float = 0.0,
    span_pct: float | None = None,
    exposure_pct: float = 0.03,
) -> dict[str, Any]:
    """Indicative SPAN + exposure margin.

    This is a simplified proxy, NOT the exchange SPAN file. Every response says
    so — and one of the blue-team compliance checks asserts that the disclaimer
    is present, because a training app that implies exchange-accurate margin is
    a real-world defect.
    """
    if lots <= 0:
        raise ValueError("lots must be at least 1")
    if lot_size <= 0:
        raise ValueError("lot_size must be positive")
    position = position.lower()
    valid = {"futures_long", "futures_short", "option_buy", "option_sell"}
    if position not in valid:
        raise ValueError(f"position must be one of {sorted(valid)}")

    contract_value = spot * lot_size * lots

    if position == "option_buy":
        total = premium * lot_size * lots
        return MarginResult(
            symbol=symbol, position=position, lots=lots, lot_size=lot_size,
            contract_value=round(contract_value, 2), span_margin=0.0, exposure_margin=0.0,
            total_margin=round(total, 2), premium_receivable=0.0,
            methodology="Long options are fully paid: margin equals the premium outgo.",
            disclaimer="Indicative only. Actual margin is set by exchange SPAN files and your broker's policy.",
        ).to_dict()

    defaults = {"futures_long": 0.12, "futures_short": 0.12, "option_sell": 0.13}
    span_rate = span_pct if span_pct is not None else defaults[position]
    span = contract_value * span_rate
    exposure = contract_value * exposure_pct
    premium_recv = premium * lot_size * lots if position == "option_sell" else 0.0

    return MarginResult(
        symbol=symbol, position=position, lots=lots, lot_size=lot_size,
        contract_value=round(contract_value, 2),
        span_margin=round(span, 2), exposure_margin=round(exposure, 2),
        total_margin=round(span + exposure, 2),
        premium_receivable=round(premium_recv, 2),
        methodology=f"SPAN proxy {span_rate:.1%} + exposure {exposure_pct:.1%} of contract value.",
        disclaimer="Indicative only. Actual margin is set by exchange SPAN files and your broker's policy.",
    ).to_dict()


# ---------------------------------------------------------------------------
# Strategy payoffs
# ---------------------------------------------------------------------------
STRATEGY_LEGS: dict[str, list[dict[str, Any]]] = {
    "long_call":       [{"type": "call", "side": "buy",  "strike_offset": 0}],
    "long_put":        [{"type": "put",  "side": "buy",  "strike_offset": 0}],
    "short_call":      [{"type": "call", "side": "sell", "strike_offset": 0}],
    "short_put":       [{"type": "put",  "side": "sell", "strike_offset": 0}],
    "long_straddle":   [{"type": "call", "side": "buy",  "strike_offset": 0},
                        {"type": "put",  "side": "buy",  "strike_offset": 0}],
    "short_straddle":  [{"type": "call", "side": "sell", "strike_offset": 0},
                        {"type": "put",  "side": "sell", "strike_offset": 0}],
    "long_strangle":   [{"type": "call", "side": "buy",  "strike_offset": 2},
                        {"type": "put",  "side": "buy",  "strike_offset": -2}],
    "bull_call_spread":[{"type": "call", "side": "buy",  "strike_offset": 0},
                        {"type": "call", "side": "sell", "strike_offset": 2}],
    "bear_put_spread": [{"type": "put",  "side": "buy",  "strike_offset": 0},
                        {"type": "put",  "side": "sell", "strike_offset": -2}],
    "iron_condor":     [{"type": "put",  "side": "buy",  "strike_offset": -4},
                        {"type": "put",  "side": "sell", "strike_offset": -2},
                        {"type": "call", "side": "sell", "strike_offset": 2},
                        {"type": "call", "side": "buy",  "strike_offset": 4}],
}


def leg_payoff(price_at_expiry: float, leg: dict[str, Any]) -> float:
    intrinsic = (
        max(price_at_expiry - leg["strike"], 0.0)
        if leg["type"] == "call"
        else max(leg["strike"] - price_at_expiry, 0.0)
    )
    sign = 1 if leg["side"] == "buy" else -1
    return sign * (intrinsic - leg["premium"]) * leg.get("quantity", 1)


def build_strategy(
    strategy: str,
    spot: float,
    strike_step: float,
    t: float,
    r: float,
    sigma: float,
    lot_size: int = 1,
) -> dict[str, Any]:
    key = strategy.lower().replace(" ", "_").replace("-", "_")
    if key not in STRATEGY_LEGS:
        raise ValueError(f"unknown strategy '{strategy}'; known: {sorted(STRATEGY_LEGS)}")
    atm = round(spot / strike_step) * strike_step
    legs = []
    for tpl in STRATEGY_LEGS[key]:
        strike = atm + tpl["strike_offset"] * strike_step
        premium = black_scholes(spot, strike, t, r, sigma, tpl["type"])["price"]
        legs.append({**tpl, "strike": float(strike), "premium": round(premium, 2), "quantity": 1})
    return analyse_payoff(legs, spot, lot_size, strategy=key)


def analyse_payoff(
    legs: list[dict[str, Any]],
    spot: float,
    lot_size: int = 1,
    points: int = 121,
    strategy: str = "custom",
) -> dict[str, Any]:
    """Payoff curve, breakevens, max profit/loss for an arbitrary leg set."""
    if not legs:
        raise ValueError("at least one leg is required")
    lo, hi = spot * 0.80, spot * 1.20
    step = (hi - lo) / (points - 1)
    curve = []
    for i in range(points):
        px = lo + i * step
        pnl = sum(leg_payoff(px, leg) for leg in legs) * lot_size
        curve.append({"price": round(px, 2), "pnl": round(pnl, 2)})

    # Bounds are computed on a wider grid than the display curve, anchored at
    # S=0 (the true downside floor) and extended far to the right, where an
    # equity/index payoff is genuinely unbounded.
    wide = [0.0] + [lo + i * step for i in range(points)] + [spot * 3, spot * 3 + step]
    wide_pnl = [sum(leg_payoff(px, leg) for leg in legs) * lot_size for px in wide]
    right_slope = wide_pnl[-1] - wide_pnl[-2]
    unlimited_profit = right_slope > 0.01
    unlimited_loss = right_slope < -0.01

    pnls = [c["pnl"] for c in curve]
    breakevens: list[float] = []
    for a, b in zip(curve, curve[1:]):
        if a["pnl"] == 0:
            breakevens.append(a["price"])
        elif a["pnl"] * b["pnl"] < 0:
            frac = abs(a["pnl"]) / (abs(a["pnl"]) + abs(b["pnl"]))
            breakevens.append(round(a["price"] + frac * (b["price"] - a["price"]), 2))

    net_premium = sum(
        (-1 if leg["side"] == "buy" else 1) * leg["premium"] * leg.get("quantity", 1) for leg in legs
    ) * lot_size

    bounded = wide_pnl[:-2]  # S=0 up to the top of the display range
    return {
        "strategy": strategy,
        "legs": legs,
        "lot_size": lot_size,
        "spot": round(spot, 2),
        "net_premium": round(net_premium, 2),
        "position_type": "credit" if net_premium > 0 else "debit",
        "max_profit": "unlimited" if unlimited_profit else round(max(bounded), 2),
        "max_loss": "unlimited" if unlimited_loss else round(min(bounded), 2),
        "breakevens": sorted(set(breakevens)),
        "payoff_curve": curve,
        "risk_note": (
            "Short option legs carry theoretically unlimited loss and are subject to margin calls."
            if any(l["side"] == "sell" for l in legs)
            else "Long-only position: maximum loss is limited to the premium paid."
        ),
        "disclaimer": "Educational payoff model. Ignores brokerage, STT, slippage and early assignment.",
    }


def pcr_interpretation(pcr: float | None) -> dict[str, Any]:
    if pcr is None:
        return {"pcr": None, "reading": "unavailable", "note": "Open-interest data missing from the source."}
    if pcr > 1.3:
        reading, note = "bullish/oversold", "High put OI relative to calls; often read as a support build-up."
    elif pcr < 0.7:
        reading, note = "bearish/overbought", "High call OI relative to puts; often read as resistance build-up."
    else:
        reading, note = "neutral", "Put and call open interest are broadly balanced."
    return {"pcr": pcr, "reading": reading, "note": note,
            "caveat": "PCR is one sentiment input among many and is not a trading signal on its own."}


def max_pain(strikes: list[dict[str, Any]]) -> dict[str, Any]:
    """Strike at which total option-writer payout is minimised."""
    usable = [s for s in strikes if s.get("strike") is not None]
    if not usable:
        return {"max_pain": None, "reason": "no strike data"}
    losses: list[tuple[float, float]] = []
    for candidate in usable:
        k = candidate["strike"]
        total = 0.0
        for row in usable:
            total += max(k - row["strike"], 0) * (row.get("call_oi") or 0)
            total += max(row["strike"] - k, 0) * (row.get("put_oi") or 0)
        losses.append((k, total))
    strike, value = min(losses, key=lambda x: x[1])
    return {
        "max_pain": strike,
        "total_writer_payout": round(value, 2),
        "note": "Strike where option writers lose least at expiry. A statistical observation, not a forecast.",
    }
