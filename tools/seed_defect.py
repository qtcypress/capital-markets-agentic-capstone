#!/usr/bin/env python3
"""Inject (or remove) a known defect, so trainees can prove the suite catches it.

    python tools/seed_defect.py --list
    python tools/seed_defect.py D1          # inject defect D1
    python tools/seed_defect.py --restore   # undo everything

Each defect is a single, surgical text substitution in one source file. The
original is backed up next to the file as <name>.orig before the first change.

Workflow for a lab:
    1. ./test.sh fast                 -> 321 pass
    2. python tools/seed_defect.py D3
    3. ./test.sh fast                 -> some cases fail; which ones, and why?
    4. python tools/seed_defect.py --restore
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

DEFECTS: dict[str, dict] = {
    "D1": {
        "file": "app/market/sources.py",
        "old": '"NIFTY":      {"lot_size": 75,',
        "new": '"NIFTY":      {"lot_size": 50,',
        "title": "Wrong NIFTY lot size in the contract master (75 -> 50)",
        "impact": "Every NIFTY margin, contract value and position-Greek figure is understated by a third.",
    },
    "D2": {
        "file": "app/market/derivatives.py",
        "old": '    gamma = (disc_q * _norm_pdf(d1)) / (spot * vol_t)',
        "new": '    gamma = (disc_q * _norm_pdf(d1)) / (strike * vol_t)',
        "title": "Gamma divided by strike instead of spot",
        "impact": "Gamma is wrong for every away-from-the-money option; hedging ratios silently drift.",
    },
    "D3": {
        "file": "app/agents/single_agent.py",
        "old": '            if call.name not in self.tool_names:',
        "new": '            if False:  # authorisation check disabled',
        "title": "Tool authorisation check removed from the agent loop",
        "impact": "The agent may invoke any registered tool, including ones it was never granted.",
    },
    "D4": {
        "file": "app/guardrails/rules.py",
        "old": '    findings += _scan(text, ADVICE_PATTERNS, "OUT-03", "high", "block")',
        "new": '    findings += _scan(text, ADVICE_PATTERNS, "OUT-03", "low", "flag")',
        "title": "Investment-advice control downgraded from block to flag",
        "impact": "Directive recommendations and guaranteed-return claims reach the user. Compliance breach.",
    },
    "D5": {
        "file": "app/market/sources.py",
        "old": '    payload = synth_fn()\n    payload.warnings.extend(errors[:2])\n    return payload',
        "new": '    payload = synth_fn()\n    payload.source = "live"\n    payload.stale = False\n    payload.warnings = []\n    return payload',
        "title": "Synthetic data mislabelled as live",
        "impact": "Generated prices are presented as real market data with no warning. The worst class of data defect.",
    },
    "D6": {
        "file": "app/rag/pipeline.py",
        "old": '        result.citations = list(dict.fromkeys(cited))',
        "new": '        result.citations = []',
        "title": "Citation extraction always returns empty",
        "impact": "Answers lose their provenance; a user cannot verify any claim against a source.",
    },
    "D7": {
        "file": "app/agents/orchestrator.py",
        "old": '            if not self.allowed(call.name):',
        "new": '            if False:  # cross-agent boundary disabled',
        "title": "Cross-agent tool boundary removed",
        "impact": "A specialist can reach another specialist's MCP server — privilege escalation.",
    },
    "D8": {
        "file": "app/rag/store.py",
        "old": '        out = list(tokens)\n        for t in tokens:\n            out.extend(SYNONYMS.get(t, []))\n        return out',
        "new": '        return list(tokens)',
        "title": "Synonym expansion disabled in retrieval",
        "impact": "Questions using trade abbreviations (CE, PE, OI, PCR, F&O) retrieve the wrong passages.",
    },
}


def _backup(path: Path) -> Path:
    orig = path.with_suffix(path.suffix + ".orig")
    if not orig.exists():
        shutil.copy2(path, orig)
    return orig


def inject(key: str) -> int:
    d = DEFECTS[key]
    path = ROOT / d["file"]
    text = path.read_text(encoding="utf-8")
    if d["old"] not in text:
        if d["new"] in text:
            print(f"{key} is already injected.")
            return 0
        print(f"ERROR: anchor text for {key} not found in {d['file']}.")
        print("The file may have been edited. Run --restore first.")
        return 1
    _backup(path)
    path.write_text(text.replace(d["old"], d["new"], 1), encoding="utf-8")
    print(f"Injected {key}: {d['title']}")
    print(f"  file:   {d['file']}")
    print(f"  impact: {d['impact']}")
    print("\nNow run:  ./test.sh fast")
    print("Which cases fail? Are they the ones you would expect? Which SHOULD have caught it?")
    return 0


def restore() -> int:
    n = 0
    for path in sorted(ROOT.rglob("*.orig")):
        target = path.with_suffix("")
        shutil.copy2(path, target)
        path.unlink()
        print(f"restored {target.relative_to(ROOT)}")
        n += 1
    print("nothing to restore" if not n else f"\n{n} file(s) restored.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("defect", nargs="?", help="defect id, e.g. D3")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--restore", action="store_true")
    args = ap.parse_args()

    if args.restore:
        return restore()
    if args.list or not args.defect:
        print("Seeded defects:\n")
        for k, d in DEFECTS.items():
            print(f"  {k}  {d['title']}")
            print(f"      {d['file']}")
            print(f"      impact: {d['impact']}\n")
        print("Usage: python tools/seed_defect.py D1   |   --restore")
        return 0
    key = args.defect.upper()
    if key not in DEFECTS:
        print(f"Unknown defect '{key}'. Use --list.")
        return 1
    return inject(key)


if __name__ == "__main__":
    raise SystemExit(main())
