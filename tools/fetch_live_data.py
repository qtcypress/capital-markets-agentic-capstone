#!/usr/bin/env python3
"""Refresh the recorded market-data snapshots from the live public APIs.

Run this once before a training session (ideally during market hours) so that
every trainee works against the same recorded data and the suites stay stable:

    python tools/fetch_live_data.py                 # default symbol set
    python tools/fetch_live_data.py NIFTY RELIANCE  # specific symbols
    python tools/fetch_live_data.py --check         # connectivity check only

Snapshots land in data/snapshots/ and are served automatically whenever a live
call fails, with `source: snapshot` and `stale: true` in the payload.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.config import SNAPSHOT_DIR  # noqa: E402
from app.market.sources import (  # noqa: E402
    CONTRACT_SPECS, _fetch_fx_live, _fetch_option_chain_live, _fetch_quote_live,
    market_is_open, save_snapshot,
)

DEFAULT_SYMBOLS = ["NIFTY", "BANKNIFTY", "FINNIFTY", "RELIANCE", "TCS", "INFY",
                   "HDFCBANK", "ICICIBANK", "SBIN", "ITC"]
CHAIN_SYMBOLS = ["NIFTY", "BANKNIFTY", "FINNIFTY"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("symbols", nargs="*", default=None)
    ap.add_argument("--check", action="store_true", help="test connectivity, write nothing")
    args = ap.parse_args()
    symbols = args.symbols or DEFAULT_SYMBOLS

    print(f"Market is {'OPEN' if market_is_open() else 'CLOSED'} right now.")
    print(f"Snapshots -> {SNAPSHOT_DIR}\n")
    ok = failed = 0

    for sym in symbols:
        try:
            payload = _fetch_quote_live(sym)
            if not args.check:
                save_snapshot(payload)
            print(f"  quote   {sym:12} {payload.data['last_price']:>12,.2f}  "
                  f"({payload.provider}, {payload.latency_ms}ms)")
            ok += 1
        except Exception as exc:  # noqa: BLE001
            print(f"  quote   {sym:12} FAILED: {type(exc).__name__}: {str(exc)[:90]}")
            failed += 1

    for sym in [s for s in CHAIN_SYMBOLS if s in symbols or not args.symbols]:
        try:
            payload = _fetch_option_chain_live(sym)
            if not args.check:
                save_snapshot(payload)
            print(f"  chain   {sym:12} {payload.data['strike_count']:>5} strikes, "
                  f"PCR {payload.data.get('pcr')}  ({payload.latency_ms}ms)")
            ok += 1
        except Exception as exc:  # noqa: BLE001
            print(f"  chain   {sym:12} FAILED: {type(exc).__name__}: {str(exc)[:90]}")
            failed += 1

    try:
        payload = _fetch_fx_live("USD", "INR")
        if not args.check:
            save_snapshot(payload)
        print(f"  fx      USD/INR      {payload.data['rate']:>12,.4f}  ({payload.provider})")
        ok += 1
    except Exception as exc:  # noqa: BLE001
        print(f"  fx      USD/INR      FAILED: {type(exc).__name__}: {str(exc)[:90]}")
        failed += 1

    print(f"\n{ok} succeeded, {failed} failed.")
    if failed and not ok:
        print("\nNo live source was reachable. Causes, in order of likelihood:")
        print("  1. No internet access, or a corporate proxy blocking these hosts.")
        print("  2. NSE blocks datacentre IPs — run this from a normal desktop connection.")
        print("  3. The market is closed and the provider returned an empty payload.")
        print("The application still works: it falls back to snapshots, then to clearly")
        print("labelled synthetic data. Provenance is always reported in the response.")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
