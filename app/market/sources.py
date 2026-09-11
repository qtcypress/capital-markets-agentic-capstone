"""Live market data from public APIs, with a recorded-snapshot safety net.

Sources used (all public, no key required):

  * Yahoo Finance chart API  -> spot / OHLC for NSE equities and indices
  * Yahoo Finance options API -> option chain (US names; used for the global lab)
  * NSE India public API      -> NIFTY / BANKNIFTY / FINNIFTY option chain
  * Frankfurter (ECB)         -> USD/INR and other FX reference rates
  * Stooq CSV                 -> index fallback quote

Design rule for testers: every fetch returns a `MarketPayload` that always
records `source` ("live" | "snapshot" | "synthetic"), `as_of`, and `stale`.
That envelope is itself a test target — a large slice of the blue-team suite
asserts on provenance metadata rather than on prices, which is what makes the
suite stable against a moving market.
"""
from __future__ import annotations

import csv
import io
import json
import math
import random
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from ..config import SNAPSHOT_DIR, get_config

IST = timezone(timedelta(hours=5, minutes=30))

YF_CHART = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
YF_OPTIONS = "https://query2.finance.yahoo.com/v7/finance/options/{symbol}"
NSE_HOME = "https://www.nseindia.com"
NSE_OPTION_CHAIN_INDEX = "https://www.nseindia.com/api/option-chain-indices?symbol={symbol}"
NSE_OPTION_CHAIN_EQUITY = "https://www.nseindia.com/api/option-chain-equities?symbol={symbol}"
NSE_QUOTE = "https://www.nseindia.com/api/quote-equity?symbol={symbol}"
FRANKFURTER = "https://api.frankfurter.app/latest?from={base}&to={quote}"
STOOQ = "https://stooq.com/q/l/?s={symbol}&f=sd2t2ohlcv&h&e=csv"

# Yahoo ticker mapping for Indian instruments.
YF_SYMBOLS = {
    "NIFTY": "^NSEI",
    "NIFTY50": "^NSEI",
    "BANKNIFTY": "^NSEBANK",
    "FINNIFTY": "NIFTY_FIN_SERVICE.NS",
    "SENSEX": "^BSESN",
    "INDIAVIX": "^INDIAVIX",
}
INDEX_SYMBOLS = {"NIFTY", "NIFTY50", "BANKNIFTY", "FINNIFTY", "MIDCPNIFTY", "SENSEX"}

# Contract specifications — used for margin, lot value and validation checks.
CONTRACT_SPECS: dict[str, dict[str, Any]] = {
    "NIFTY":      {"lot_size": 75,  "tick": 0.05, "strike_step": 50,  "segment": "index",  "expiry_day": "Thursday"},
    "BANKNIFTY":  {"lot_size": 30,  "tick": 0.05, "strike_step": 100, "segment": "index",  "expiry_day": "Wednesday"},
    "FINNIFTY":   {"lot_size": 65,  "tick": 0.05, "strike_step": 50,  "segment": "index",  "expiry_day": "Tuesday"},
    "MIDCPNIFTY": {"lot_size": 120, "tick": 0.05, "strike_step": 25,  "segment": "index",  "expiry_day": "Monday"},
    "RELIANCE":   {"lot_size": 500, "tick": 0.05, "strike_step": 20,  "segment": "stock",  "expiry_day": "Thursday"},
    "TCS":        {"lot_size": 175, "tick": 0.05, "strike_step": 50,  "segment": "stock",  "expiry_day": "Thursday"},
    "INFY":       {"lot_size": 400, "tick": 0.05, "strike_step": 20,  "segment": "stock",  "expiry_day": "Thursday"},
    "HDFCBANK":   {"lot_size": 550, "tick": 0.05, "strike_step": 20,  "segment": "stock",  "expiry_day": "Thursday"},
    "ICICIBANK":  {"lot_size": 700, "tick": 0.05, "strike_step": 10,  "segment": "stock",  "expiry_day": "Thursday"},
    "SBIN":       {"lot_size": 750, "tick": 0.05, "strike_step": 10,  "segment": "stock",  "expiry_day": "Thursday"},
    "ITC":        {"lot_size": 1600,"tick": 0.05, "strike_step": 5,   "segment": "stock",  "expiry_day": "Thursday"},
    "AXISBANK":   {"lot_size": 625, "tick": 0.05, "strike_step": 10,  "segment": "stock",  "expiry_day": "Thursday"},
}

# Reference levels used only to seed the synthetic generator when both the live
# API and the snapshot are unavailable. They are labelled as synthetic.
REFERENCE_LEVELS = {
    "NIFTY": 24800.0, "BANKNIFTY": 54200.0, "FINNIFTY": 25400.0, "MIDCPNIFTY": 12600.0,
    "SENSEX": 81200.0, "RELIANCE": 2960.0, "TCS": 4120.0, "INFY": 1880.0,
    "HDFCBANK": 1710.0, "ICICIBANK": 1290.0, "SBIN": 840.0, "ITC": 465.0, "AXISBANK": 1180.0,
    "INDIAVIX": 13.4,
}


class MarketDataError(RuntimeError):
    pass


@dataclass
class MarketPayload:
    """Every market call returns this envelope. Provenance is first class."""

    kind: str
    symbol: str
    data: dict[str, Any]
    source: str = "live"          # live | snapshot | synthetic
    as_of: str = ""
    stale: bool = False
    latency_ms: int = 0
    provider: str = ""
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _now_iso() -> str:
    return datetime.now(IST).isoformat(timespec="seconds")


def normalise_symbol(symbol: str) -> str:
    return (symbol or "").upper().replace(" ", "").replace("-", "").strip()


def market_is_open(now: datetime | None = None) -> bool:
    now = now or datetime.now(IST)
    if now.weekday() >= 5:
        return False
    open_t = now.replace(hour=9, minute=15, second=0, microsecond=0)
    close_t = now.replace(hour=15, minute=30, second=0, microsecond=0)
    return open_t <= now <= close_t


# ---------------------------------------------------------------------------
# Snapshot cache
# ---------------------------------------------------------------------------
def _snapshot_path(kind: str, symbol: str):
    safe = normalise_symbol(symbol) or "NA"
    return SNAPSHOT_DIR / f"{kind}__{safe}.json"


def save_snapshot(payload: MarketPayload) -> None:
    try:
        path = _snapshot_path(payload.kind, payload.symbol)
        path.write_text(json.dumps(payload.to_dict(), indent=2), encoding="utf-8")
    except OSError:
        pass


def load_snapshot(kind: str, symbol: str) -> MarketPayload | None:
    path = _snapshot_path(kind, symbol)
    if not path.exists():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    raw.pop("latency_ms", None)
    payload = MarketPayload(**{**raw, "source": "snapshot", "stale": True})
    payload.warnings = list(payload.warnings) + ["served from recorded snapshot; live API unavailable"]
    return payload


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------
def _client(cookies: httpx.Cookies | None = None) -> httpx.Client:
    cfg = get_config().market
    return httpx.Client(
        timeout=cfg.timeout_s,
        follow_redirects=True,
        cookies=cookies,
        headers={
            "User-Agent": cfg.user_agent,
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
        },
    )


def _nse_client() -> httpx.Client:
    """NSE requires a homepage visit first to obtain cookies.

    The returned client has already issued requests, so it must NOT be used as
    a context manager again (httpx refuses to re-enter an opened client) —
    callers close it in a finally block instead.
    """
    client = _client()
    try:
        client.get(NSE_HOME)
        client.get(f"{NSE_HOME}/option-chain")
    except httpx.HTTPError:
        pass
    return client


# ---------------------------------------------------------------------------
# Live fetchers
# ---------------------------------------------------------------------------
def _fetch_quote_live(symbol: str) -> MarketPayload:
    sym = normalise_symbol(symbol)
    yf = YF_SYMBOLS.get(sym, f"{sym}.NS")
    started = time.perf_counter()
    with _client() as client:
        r = client.get(YF_CHART.format(symbol=yf), params={"range": "5d", "interval": "1d"})
        r.raise_for_status()
        body = r.json()
    result = (body.get("chart") or {}).get("result") or []
    if not result:
        raise MarketDataError(f"Yahoo returned no chart data for {yf}")
    meta = result[0].get("meta", {})
    quotes = ((result[0].get("indicators") or {}).get("quote") or [{}])[0]
    closes = [c for c in (quotes.get("close") or []) if c is not None]
    price = meta.get("regularMarketPrice") or (closes[-1] if closes else None)
    if price is None:
        raise MarketDataError(f"No price in Yahoo payload for {yf}")
    prev = meta.get("chartPreviousClose") or meta.get("previousClose") or (closes[-2] if len(closes) > 1 else price)
    data = {
        "symbol": sym,
        "yahoo_symbol": yf,
        "last_price": round(float(price), 2),
        "previous_close": round(float(prev), 2),
        "change": round(float(price) - float(prev), 2),
        "change_pct": round((float(price) - float(prev)) / float(prev) * 100, 2) if prev else 0.0,
        "day_high": meta.get("regularMarketDayHigh"),
        "day_low": meta.get("regularMarketDayLow"),
        "currency": meta.get("currency", "INR"),
        "exchange": meta.get("exchangeName", "NSI"),
        "is_index": sym in INDEX_SYMBOLS,
        "lot_size": CONTRACT_SPECS.get(sym, {}).get("lot_size"),
        "market_open": market_is_open(),
        "history": [
            {"close": round(float(c), 2)} for c in closes[-5:]
        ],
    }
    return MarketPayload(
        kind="quote", symbol=sym, data=data, source="live",
        as_of=_now_iso(), provider="yahoo-finance",
        latency_ms=int((time.perf_counter() - started) * 1000),
    )


def _fetch_quote_stooq(symbol: str) -> MarketPayload:
    """Secondary live source for indices when Yahoo is unreachable."""
    sym = normalise_symbol(symbol)
    stooq_map = {"NIFTY": "^nsei", "BANKNIFTY": "^bsesn", "SENSEX": "^bsesn"}
    code = stooq_map.get(sym)
    if not code:
        raise MarketDataError(f"No Stooq mapping for {sym}")
    started = time.perf_counter()
    with _client() as client:
        r = client.get(STOOQ.format(symbol=code))
        r.raise_for_status()
        rows = list(csv.DictReader(io.StringIO(r.text)))
    if not rows or rows[0].get("Close") in (None, "N/D"):
        raise MarketDataError("Stooq returned no usable row")
    row = rows[0]
    close, open_ = float(row["Close"]), float(row["Open"])
    return MarketPayload(
        kind="quote", symbol=sym, source="live", as_of=_now_iso(), provider="stooq",
        latency_ms=int((time.perf_counter() - started) * 1000),
        data={
            "symbol": sym, "last_price": close, "previous_close": open_,
            "change": round(close - open_, 2),
            "change_pct": round((close - open_) / open_ * 100, 2) if open_ else 0.0,
            "day_high": float(row["High"]), "day_low": float(row["Low"]),
            "currency": "INR", "exchange": "NSE", "is_index": True,
            "lot_size": CONTRACT_SPECS.get(sym, {}).get("lot_size"),
            "market_open": market_is_open(), "history": [],
        },
    )


def _fetch_option_chain_live(symbol: str, expiry: str | None = None) -> MarketPayload:
    sym = normalise_symbol(symbol)
    url = (NSE_OPTION_CHAIN_INDEX if sym in INDEX_SYMBOLS else NSE_OPTION_CHAIN_EQUITY).format(symbol=sym)
    started = time.perf_counter()
    client = _nse_client()
    try:
        r = client.get(url)
        r.raise_for_status()
        body = r.json()
    finally:
        client.close()
    records = body.get("records") or {}
    all_expiries = records.get("expiryDates") or []
    underlying = records.get("underlyingValue")
    chosen = expiry if expiry in all_expiries else (all_expiries[0] if all_expiries else None)
    rows = []
    for item in records.get("data", []):
        if chosen and item.get("expiryDate") != chosen:
            continue
        ce, pe = item.get("CE") or {}, item.get("PE") or {}
        rows.append({
            "strike": item.get("strikePrice"),
            "expiry": item.get("expiryDate"),
            "call_ltp": ce.get("lastPrice"), "call_oi": ce.get("openInterest"),
            "call_oi_change": ce.get("changeinOpenInterest"), "call_iv": ce.get("impliedVolatility"),
            "call_volume": ce.get("totalTradedVolume"), "call_bid": ce.get("bidprice"), "call_ask": ce.get("askPrice"),
            "put_ltp": pe.get("lastPrice"), "put_oi": pe.get("openInterest"),
            "put_oi_change": pe.get("changeinOpenInterest"), "put_iv": pe.get("impliedVolatility"),
            "put_volume": pe.get("totalTradedVolume"), "put_bid": pe.get("bidprice"), "put_ask": pe.get("askPrice"),
        })
    rows.sort(key=lambda r: r["strike"] or 0)
    total_ce_oi = sum(r["call_oi"] or 0 for r in rows)
    total_pe_oi = sum(r["put_oi"] or 0 for r in rows)
    data = {
        "symbol": sym, "underlying_value": underlying, "expiry": chosen,
        "expiries": all_expiries, "strikes": rows,
        "total_call_oi": total_ce_oi, "total_put_oi": total_pe_oi,
        "pcr": round(total_pe_oi / total_ce_oi, 3) if total_ce_oi else None,
        "lot_size": CONTRACT_SPECS.get(sym, {}).get("lot_size"),
        "strike_count": len(rows),
    }
    return MarketPayload(
        kind="option_chain", symbol=sym, data=data, source="live", as_of=_now_iso(),
        provider="nse-india", latency_ms=int((time.perf_counter() - started) * 1000),
    )


def _fetch_fx_live(base: str = "USD", quote: str = "INR") -> MarketPayload:
    started = time.perf_counter()
    with _client() as client:
        r = client.get(FRANKFURTER.format(base=base, quote=quote))
        r.raise_for_status()
        body = r.json()
    rate = (body.get("rates") or {}).get(quote)
    if rate is None:
        raise MarketDataError(f"No {base}/{quote} rate in Frankfurter response")
    return MarketPayload(
        kind="fx", symbol=f"{base}{quote}", source="live", as_of=_now_iso(),
        provider="frankfurter-ecb", latency_ms=int((time.perf_counter() - started) * 1000),
        data={"base": base, "quote": quote, "rate": float(rate), "reference_date": body.get("date")},
    )


def _fetch_us_option_chain_live(symbol: str) -> MarketPayload:
    sym = symbol.upper()
    started = time.perf_counter()
    with _client() as client:
        r = client.get(YF_OPTIONS.format(symbol=sym))
        r.raise_for_status()
        body = r.json()
    result = ((body.get("optionChain") or {}).get("result") or [])
    if not result:
        raise MarketDataError(f"No option chain for {sym}")
    node = result[0]
    chain = (node.get("options") or [{}])[0]
    calls = {c["strike"]: c for c in chain.get("calls", [])}
    puts = {p["strike"]: p for p in chain.get("puts", [])}
    rows = [
        {
            "strike": k,
            "call_ltp": calls.get(k, {}).get("lastPrice"), "call_oi": calls.get(k, {}).get("openInterest"),
            "call_iv": round((calls.get(k, {}).get("impliedVolatility") or 0) * 100, 2),
            "put_ltp": puts.get(k, {}).get("lastPrice"), "put_oi": puts.get(k, {}).get("openInterest"),
            "put_iv": round((puts.get(k, {}).get("impliedVolatility") or 0) * 100, 2),
        }
        for k in sorted(set(calls) | set(puts))
    ]
    return MarketPayload(
        kind="option_chain", symbol=sym, source="live", as_of=_now_iso(), provider="yahoo-options",
        latency_ms=int((time.perf_counter() - started) * 1000),
        data={
            "symbol": sym, "underlying_value": (node.get("quote") or {}).get("regularMarketPrice"),
            "expiry": chain.get("expirationDate"), "expiries": node.get("expirationDates", []),
            "strikes": rows, "strike_count": len(rows),
            "total_call_oi": sum(r["call_oi"] or 0 for r in rows),
            "total_put_oi": sum(r["put_oi"] or 0 for r in rows),
            "pcr": None, "lot_size": 100,
        },
    )


# ---------------------------------------------------------------------------
# Synthetic generator — last resort, always labelled
# ---------------------------------------------------------------------------
def _synthetic_quote(symbol: str) -> MarketPayload:
    sym = normalise_symbol(symbol)
    base = REFERENCE_LEVELS.get(sym, 1000.0)
    rng = random.Random(f"{sym}-{datetime.now(IST).date()}")
    price = round(base * (1 + rng.uniform(-0.015, 0.015)), 2)
    prev = round(base * (1 + rng.uniform(-0.012, 0.012)), 2)
    return MarketPayload(
        kind="quote", symbol=sym, source="synthetic", stale=True, as_of=_now_iso(),
        provider="synthetic-generator",
        warnings=["SYNTHETIC DATA: no live API and no snapshot available; do not use for analysis"],
        data={
            "symbol": sym, "last_price": price, "previous_close": prev,
            "change": round(price - prev, 2),
            "change_pct": round((price - prev) / prev * 100, 2),
            "day_high": round(price * 1.006, 2), "day_low": round(price * 0.994, 2),
            "currency": "INR", "exchange": "NSE", "is_index": sym in INDEX_SYMBOLS,
            "lot_size": CONTRACT_SPECS.get(sym, {}).get("lot_size"),
            "market_open": market_is_open(), "history": [],
        },
    )


def _synthetic_option_chain(symbol: str, expiry: str | None = None) -> MarketPayload:
    from .derivatives import black_scholes

    sym = normalise_symbol(symbol)
    spot = _synthetic_quote(sym).data["last_price"]
    spec = CONTRACT_SPECS.get(sym, {"strike_step": 50, "lot_size": 50})
    step = spec["strike_step"]
    atm = round(spot / step) * step
    rng = random.Random(f"chain-{sym}-{datetime.now(IST).date()}")
    exp_date = (datetime.now(IST) + timedelta(days=(3 - datetime.now(IST).weekday()) % 7 or 7)).date()
    t = max((exp_date - datetime.now(IST).date()).days, 1) / 365
    rows = []
    for i in range(-10, 11):
        strike = atm + i * step
        iv = 0.13 + abs(i) * 0.004 + rng.uniform(-0.004, 0.004)
        call = black_scholes(spot, strike, t, get_config().market.risk_free_rate, iv, "call")
        put = black_scholes(spot, strike, t, get_config().market.risk_free_rate, iv, "put")
        moneyness = abs(i)
        oi_base = int(90000 * math.exp(-0.18 * moneyness))
        rows.append({
            "strike": float(strike), "expiry": exp_date.isoformat(),
            "call_ltp": round(call["price"], 2), "call_oi": oi_base + rng.randint(0, 9000),
            "call_oi_change": rng.randint(-9000, 9000), "call_iv": round(iv * 100, 2),
            "call_volume": rng.randint(1000, 220000),
            "call_bid": round(call["price"] * 0.995, 2), "call_ask": round(call["price"] * 1.005, 2),
            "put_ltp": round(put["price"], 2), "put_oi": oi_base + rng.randint(0, 9000),
            "put_oi_change": rng.randint(-9000, 9000), "put_iv": round(iv * 100, 2),
            "put_volume": rng.randint(1000, 220000),
            "put_bid": round(put["price"] * 0.995, 2), "put_ask": round(put["price"] * 1.005, 2),
        })
    tce = sum(r["call_oi"] for r in rows)
    tpe = sum(r["put_oi"] for r in rows)
    return MarketPayload(
        kind="option_chain", symbol=sym, source="synthetic", stale=True, as_of=_now_iso(),
        provider="synthetic-generator",
        warnings=["SYNTHETIC DATA: Black-Scholes generated chain; not real market prices"],
        data={
            "symbol": sym, "underlying_value": spot, "expiry": exp_date.isoformat(),
            "expiries": [exp_date.isoformat()], "strikes": rows,
            "total_call_oi": tce, "total_put_oi": tpe, "pcr": round(tpe / tce, 3) if tce else None,
            "lot_size": spec.get("lot_size"), "strike_count": len(rows),
        },
    )


def _synthetic_fx(base: str, quote: str) -> MarketPayload:
    rng = random.Random(f"{base}{quote}-{datetime.now(IST).date()}")
    ref = {"USDINR": 83.5, "EURINR": 90.4, "GBPINR": 105.8}.get(f"{base}{quote}", 1.0)
    return MarketPayload(
        kind="fx", symbol=f"{base}{quote}", source="synthetic", stale=True, as_of=_now_iso(),
        provider="synthetic-generator",
        warnings=["SYNTHETIC DATA: reference FX rate, not a live quote"],
        data={"base": base, "quote": quote, "rate": round(ref * (1 + rng.uniform(-0.004, 0.004)), 4),
              "reference_date": datetime.now(IST).date().isoformat()},
    )


# ---------------------------------------------------------------------------
# Public API — live first, then snapshot, then synthetic
# ---------------------------------------------------------------------------
def _resolve(kind: str, symbol: str, live_fns: list, synth_fn) -> MarketPayload:
    cfg = get_config().market
    errors: list[str] = []

    if cfg.mode != "snapshot":
        for fn in live_fns:
            try:
                payload = fn()
                save_snapshot(payload)
                return payload
            except Exception as exc:  # noqa: BLE001 - degradation is the point
                errors.append(f"{getattr(fn, '__name__', 'source')}: {type(exc).__name__}: {exc}")

    if cfg.mode == "live" and not cfg.allow_stale:
        raise MarketDataError("; ".join(errors) or "live fetch failed and stale data is disallowed")

    snap = load_snapshot(kind, symbol)
    if snap is not None:
        snap.warnings.extend(errors[:2])
        return snap

    payload = synth_fn()
    payload.warnings.extend(errors[:2])
    return payload


def get_quote(symbol: str) -> MarketPayload:
    sym = normalise_symbol(symbol)
    return _resolve(
        "quote", sym,
        [lambda: _fetch_quote_live(sym), lambda: _fetch_quote_stooq(sym)],
        lambda: _synthetic_quote(sym),
    )


def get_option_chain(symbol: str, expiry: str | None = None) -> MarketPayload:
    sym = normalise_symbol(symbol)
    live: list = [lambda: _fetch_option_chain_live(sym, expiry)]
    if sym not in CONTRACT_SPECS and sym not in INDEX_SYMBOLS:
        live.append(lambda: _fetch_us_option_chain_live(sym))
    return _resolve("option_chain", sym, live, lambda: _synthetic_option_chain(sym, expiry))


def get_fx_rate(base: str = "USD", quote: str = "INR") -> MarketPayload:
    base, quote = base.upper(), quote.upper()
    return _resolve(
        "fx", f"{base}{quote}",
        [lambda: _fetch_fx_live(base, quote)],
        lambda: _synthetic_fx(base, quote),
    )


def get_futures(symbol: str) -> MarketPayload:
    """Synthetic futures quote derived from the live spot + cost of carry."""
    sym = normalise_symbol(symbol)
    spot_payload = get_quote(sym)
    spot = spot_payload.data["last_price"]
    r = get_config().market.risk_free_rate
    now = datetime.now(IST)
    days_to_expiry = max((_last_thursday(now) - now.date()).days, 1)
    t = days_to_expiry / 365
    fair = spot * math.exp(r * t)
    basis = round(fair - spot, 2)
    return MarketPayload(
        kind="futures", symbol=sym, source=spot_payload.source, stale=spot_payload.stale,
        as_of=_now_iso(), provider=f"derived:{spot_payload.provider}",
        warnings=spot_payload.warnings + ["futures price is model-derived (spot x cost of carry), not an exchange quote"],
        data={
            "symbol": sym, "spot": spot, "fair_value": round(fair, 2), "basis": basis,
            "annualised_carry_pct": round(r * 100, 2), "days_to_expiry": days_to_expiry,
            "expiry": _last_thursday(now).isoformat(),
            "lot_size": CONTRACT_SPECS.get(sym, {}).get("lot_size"),
            "contract_value": round(fair * (CONTRACT_SPECS.get(sym, {}).get("lot_size") or 1), 2),
        },
    )


def _last_thursday(now: datetime):
    year, month = now.year, now.month
    d = datetime(year, month, 28, tzinfo=IST)
    while d.month == month:
        d += timedelta(days=1)
    d -= timedelta(days=1)
    while d.weekday() != 3:
        d -= timedelta(days=1)
    if d.date() < now.date():
        month = month % 12 + 1
        year = year + (1 if month == 1 else 0)
        return _last_thursday(datetime(year, month, 1, tzinfo=IST))
    return d.date()


def get_contract_spec(symbol: str) -> dict[str, Any]:
    sym = normalise_symbol(symbol)
    spec = CONTRACT_SPECS.get(sym)
    if not spec:
        raise MarketDataError(f"No contract specification on file for {sym}")
    return {"symbol": sym, **spec}


def list_supported_symbols() -> list[str]:
    return sorted(CONTRACT_SPECS)
