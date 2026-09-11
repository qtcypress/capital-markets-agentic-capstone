"""Independently implemented financial maths, used as the answer key.

The single most common mistake in testing a calculation is checking the system
against itself. If `test_margin()` calls `calculate_margin()` to work out what
the answer should be, the test passes whatever the function does — including
whatever it does wrong.

So nothing in this file imports from `app/`. Every value here is computed from
first principles with the standard library, and where a closed form exists it is
written out rather than looked up. That makes these functions a genuine second
opinion, which is the only kind worth asserting against.
"""
from __future__ import annotations

import math
from datetime import date

# ---------------------------------------------------------------------------
# Returns
# ---------------------------------------------------------------------------
def cagr(begin: float, end: float, years: float) -> float:
    """Compound annual growth rate."""
    if begin <= 0 or years <= 0:
        raise ValueError("begin value and years must be positive")
    return (end / begin) ** (1.0 / years) - 1.0


def compound_interest(principal: float, rate: float, years: float, compounds_per_year: int = 4) -> float:
    """Maturity value of a deposit compounded n times a year."""
    n = compounds_per_year
    return principal * (1 + rate / n) ** (n * years)


def xirr(flows: list[tuple[date, float]], guess: float = 0.1) -> float:
    """Internal rate of return on irregularly dated cash flows (Newton, then bisection).

    Sign convention: contributions negative, redemption positive.
    """
    if len(flows) < 2:
        raise ValueError("need at least two cash flows")
    t0 = flows[0][0]
    days = [(d - t0).days / 365.0 for d, _ in flows]
    amounts = [a for _, a in flows]

    def npv(rate: float) -> float:
        return sum(a / (1 + rate) ** t for a, t in zip(amounts, days))

    rate = guess
    for _ in range(100):
        f = npv(rate)
        # numeric derivative — the analytic one buys nothing at this size
        h = 1e-6
        d = (npv(rate + h) - f) / h
        if abs(d) < 1e-12:
            break
        step = f / d
        rate -= step
        if rate <= -0.999:
            rate = -0.9
        if abs(step) < 1e-10:
            return rate
    lo, hi = -0.9999, 10.0
    for _ in range(300):
        mid = (lo + hi) / 2
        if npv(lo) * npv(mid) <= 0:
            hi = mid
        else:
            lo = mid
    return (lo + hi) / 2


def weighted_return(weights: list[float], returns: list[float]) -> float:
    total = sum(weights)
    if total <= 0:
        raise ValueError("weights must sum to a positive number")
    return sum(w * r for w, r in zip(weights, returns)) / total


def sharpe_ratio(portfolio_return: float, risk_free: float, volatility: float) -> float:
    if volatility <= 0:
        raise ValueError("volatility must be positive")
    return (portfolio_return - risk_free) / volatility


def tracking_error(fund: list[float], benchmark: list[float]) -> float:
    """Standard deviation of the return differences, as a population figure."""
    diffs = [f - b for f, b in zip(fund, benchmark)]
    mean = sum(diffs) / len(diffs)
    var = sum((d - mean) ** 2 for d in diffs) / len(diffs)
    return math.sqrt(var)


def expense_drag(gross_return: float, expense_ratio: float, years: float, amount: float) -> float:
    """Rupees given up to the expense ratio over the holding period."""
    gross = amount * (1 + gross_return) ** years
    net = amount * (1 + gross_return - expense_ratio) ** years
    return gross - net


# ---------------------------------------------------------------------------
# Bonds
# ---------------------------------------------------------------------------
def bond_price(face: float, coupon_rate: float, ytm: float, years: int, freq: int = 2) -> float:
    c = face * coupon_rate / freq
    n = years * freq
    y = ytm / freq
    return sum(c / (1 + y) ** t for t in range(1, n + 1)) + face / (1 + y) ** n


def macaulay_duration(face: float, coupon_rate: float, ytm: float, years: int, freq: int = 2) -> float:
    c = face * coupon_rate / freq
    n = years * freq
    y = ytm / freq
    price = bond_price(face, coupon_rate, ytm, years, freq)
    weighted = sum((t / freq) * (c / (1 + y) ** t) for t in range(1, n + 1))
    weighted += years * (face / (1 + y) ** n)
    return weighted / price


# ---------------------------------------------------------------------------
# Options
# ---------------------------------------------------------------------------
def _norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def black_scholes(spot: float, strike: float, rate: float, vol: float, years: float,
                  kind: str = "call") -> float:
    """Black-Scholes-Merton price, written out rather than imported."""
    if years <= 0 or vol <= 0:
        intrinsic = max(0.0, spot - strike) if kind == "call" else max(0.0, strike - spot)
        return intrinsic
    d1 = (math.log(spot / strike) + (rate + 0.5 * vol * vol) * years) / (vol * math.sqrt(years))
    d2 = d1 - vol * math.sqrt(years)
    if kind == "call":
        return spot * _norm_cdf(d1) - strike * math.exp(-rate * years) * _norm_cdf(d2)
    return strike * math.exp(-rate * years) * _norm_cdf(-d2) - spot * _norm_cdf(-d1)


def option_delta(spot: float, strike: float, rate: float, vol: float, years: float,
                 kind: str = "call") -> float:
    d1 = (math.log(spot / strike) + (rate + 0.5 * vol * vol) * years) / (vol * math.sqrt(years))
    return _norm_cdf(d1) if kind == "call" else _norm_cdf(d1) - 1.0


def breakeven(strike: float, premium: float, kind: str = "call") -> float:
    return strike + premium if kind == "call" else strike - premium


def put_call_parity_gap(call: float, put: float, spot: float, strike: float,
                        rate: float, years: float) -> float:
    """C - P - S + K*e^(-rt). Zero for a consistent pair."""
    return call - put - spot + strike * math.exp(-rate * years)


# ---------------------------------------------------------------------------
# Indian market costs and taxes (illustrative rates, stated in the corpus)
# ---------------------------------------------------------------------------
STT_DELIVERY_EQUITY = 0.001       # 0.1% on both buy and sell
STT_FUTURES_SELL = 0.0002         # 0.02% on the sell side
STT_OPTIONS_SELL_PREMIUM = 0.001  # 0.1% of premium on the sell side
LTCG_EQUITY = 0.125               # long-term capital gains on listed equity
STCG_EQUITY = 0.20                # short-term capital gains on listed equity
LTCG_EXEMPTION = 125_000.0


def capital_gains_tax(buy_value: float, sell_value: float, holding_days: int,
                      exemption_used: float = 0.0) -> float:
    gain = sell_value - buy_value
    if gain <= 0:
        return 0.0
    if holding_days > 365:
        taxable = max(0.0, gain - max(0.0, LTCG_EXEMPTION - exemption_used))
        return taxable * LTCG_EQUITY
    return gain * STCG_EQUITY


def transaction_cost(value: float, side: str = "buy", brokerage_rate: float = 0.0003,
                     brokerage_cap: float = 20.0) -> dict[str, float]:
    """Brokerage + STT + exchange charges + GST + stamp duty on a delivery trade."""
    brokerage = min(value * brokerage_rate, brokerage_cap)
    stt = value * STT_DELIVERY_EQUITY
    exchange = value * 0.0000297
    sebi = value * 0.000001
    stamp = value * 0.00015 if side == "buy" else 0.0
    gst = 0.18 * (brokerage + exchange + sebi)
    total = brokerage + stt + exchange + sebi + stamp + gst
    return {"brokerage": brokerage, "stt": stt, "exchange": exchange, "sebi": sebi,
            "stamp": stamp, "gst": gst, "total": total}


def futures_initial_margin(contract_value: float, span_pct: float, exposure_pct: float) -> float:
    return contract_value * (span_pct + exposure_pct)


# ---------------------------------------------------------------------------
# Equity ratios
# ---------------------------------------------------------------------------
def eps(net_profit: float, shares_outstanding: float) -> float:
    return net_profit / shares_outstanding


def pe_ratio(price: float, earnings_per_share: float) -> float:
    if earnings_per_share <= 0:
        raise ValueError("P/E is undefined for non-positive EPS")
    return price / earnings_per_share


def dividend_yield(dividend_per_share: float, price: float) -> float:
    return dividend_per_share / price


def convert(amount: float, rate: float) -> float:
    return amount * rate


def within(actual: float, expected: float, tolerance: float) -> bool:
    """Relative tolerance, with an absolute floor so near-zero values behave."""
    return abs(actual - expected) <= max(tolerance * abs(expected), 1e-9)
