#!/usr/bin/env python3
"""Run the YAML suites directly (no pytest) and print a summary.

Usage:
  python tools/run_suite.py                 # everything
  python tools/run_suite.py blue            # one suite
  python tools/run_suite.py blue --file tests/suites/blue/01-rag.yaml
  python tools/run_suite.py --json reports/last.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tests.runner.harness import load_cases, run_case, summarise  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("suite", nargs="?", choices=["blue", "red"], default=None)
    ap.add_argument("--file", help="run only cases from this YAML file")
    ap.add_argument("--id", help="run only this case id")
    ap.add_argument("--category", help="run only this category")
    ap.add_argument("--json", help="write full results as JSON here")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    cases = load_cases(args.suite)
    if args.file:
        want = Path(args.file).name
        cases = [c for c in cases if c.get("_file") == want]
    if args.id:
        cases = [c for c in cases if c.get("id") == args.id]
    if args.category:
        cases = [c for c in cases if c.get("category") == args.category]
    if not cases:
        print("No cases matched.")
        return 1

    results = []
    for i, case in enumerate(cases, 1):
        r = run_case(case)
        results.append(r)
        if not args.quiet:
            mark = "PASS" if r["passed"] else "FAIL"
            print(f"[{i:3}/{len(cases)}] {mark}  {r['id']:22} {r['title'][:64]}")
            if not r["passed"]:
                for c in r["checks"]:
                    if not c["passed"]:
                        print(f"          x {c['type']}: {c['message']}")
                if r["error"]:
                    print(f"          ! {r['error']}")

    s = summarise(results)
    print("\n" + "=" * 72)
    print(f"  {s['passed']}/{s['total']} passed ({s['pass_rate']}%)  in {s['total_duration_ms']}ms")
    print("=" * 72)
    for cat, v in sorted(s["by_category"].items()):
        flag = "" if v["passed"] == v["total"] else "  <-- failures"
        print(f"  {cat:32} {v['passed']:3}/{v['total']:3}{flag}")

    if args.json:
        out = Path(args.json)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps({"summary": s, "results": results}, indent=2, default=str))
        print(f"\nJSON written to {out}")

    return 0 if s["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
