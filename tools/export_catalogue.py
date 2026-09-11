"""Export the IEEE workbook into the JSON catalogue the web console serves.

Why a build step rather than reading the .xlsx at runtime
--------------------------------------------------------
The running application has no spreadsheet library and should not grow one:
`openpyxl` is a test-time dependency, and adding it to `requirements.txt` puts
17MB and a parser nobody needs into a free-tier container. The catalogue is
static between releases, so it is exported once, committed, and served as data.

Run after editing the workbook or the bindings:

    python tools/export_catalogue.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import openpyxl
import yaml

ROOT = Path(__file__).resolve().parent.parent
WORKBOOK = ROOT / "tests" / "ieee" / "Capital_Markets_GenAI_Agent_Test_Suite_IEEE.xlsx"
BINDINGS = ROOT / "tests" / "ieee" / "bindings.yaml"
OUT = ROOT / "app" / "data" / "catalogue.json"

SHEETS = ("GenAI Test Cases", "Agent Test Cases")
COL = {"id": 1, "category": 2, "requirement": 3, "objective": 4, "preconditions": 5,
       "data": 6, "steps": 7, "expected": 8, "special": 9, "depends": 10, "priority": 11,
       "type": 12}

# Which application a trainee is testing when they run this case. The workbook
# is filed by requirement area; a tester is assigned a pipeline.
SUITE_BY_EXECUTOR = {
    "rag_query": "rag", "rag_refusal": "rag", "no_fabrication": "rag", "ragas_metric": "rag",
    "citation_check": "rag", "persona_pair": "rag", "style_check": "rag", "conversation": "rag",
    "localisation": "rag", "robustness": "rag", "latency": "rag", "guardrail_block": "rag",
    "injection_block": "rag", "leakage_block": "rag",
    "agent_tool": "agent", "agent_tool_error": "agent", "agent_plan": "agent",
    "agent_react": "agent", "agent_state": "agent", "approval_gate": "agent",
    "autonomy_boundary": "agent", "agent_redteam": "agent", "escalation": "agent",
    "e2e_scenario": "agent", "trace_audit": "agent", "tool_contract": "agent",
    "calculation": "agent", "market_feed": "agent",
    "multi_agent": "multi", "concurrency": "multi", "blue_team": "multi", "regression": "multi",
}

# Executors that spawn threads or hammer the pipeline. Runnable from a laptop,
# not from a shared free-tier instance serving a class.
HEAVY = {"latency", "concurrency"}


def main() -> int:
    if not WORKBOOK.exists():
        print(f"Workbook not found: {WORKBOOK}", file=sys.stderr)
        return 2
    bindings = yaml.safe_load(BINDINGS.read_text())
    wb = openpyxl.load_workbook(WORKBOOK, read_only=True)

    cases = []
    for sheet in SHEETS:
        for row in wb[sheet].iter_rows(min_row=2, values_only=True):
            case_id = row[COL["id"] - 1]
            if not case_id:
                continue
            binding = bindings.get(case_id) or {}
            executor = binding.get("executor", "")
            category = row[COL["category"] - 1] or ""
            sent = (binding.get("input") or binding.get("scenario") or binding.get("behaviour")
                    or binding.get("metric") or binding.get("gate") or binding.get("boundary")
                    or binding.get("mode") or binding.get("attribute") or "")
            cases.append({
                "id": case_id,
                "suite": SUITE_BY_EXECUTOR.get(executor, "agent"),
                "area": case_id.split("_")[2],
                "category": category,
                "requirement": row[COL["requirement"] - 1] or "",
                "objective": row[COL["objective"] - 1] or "",
                "preconditions": row[COL["preconditions"] - 1] or "",
                "data": row[COL["data"] - 1] or "",
                "steps": row[COL["steps"] - 1] or "",
                "expected": row[COL["expected"] - 1] or "",
                "priority": row[COL["priority"] - 1] or "",
                "type": row[COL["type"] - 1] or "",
                "executor": executor,
                "capability": binding.get("capability", "unbound"),
                "input": str(sent)[:600],
                "note": binding.get("note", ""),
                "runnable": bool(executor) and executor not in HEAVY,
                "heavy": executor in HEAVY,
            })

    areas: dict[str, dict] = {}
    for case in cases:
        entry = areas.setdefault(case["area"], {"area": case["area"],
                                                "category": case["category"], "count": 0})
        entry["count"] += 1

    payload = {
        "generated_from": WORKBOOK.name,
        "cases": cases,
        "areas": sorted(areas.values(), key=lambda a: a["area"]),
        "counts": {
            "total": len(cases),
            "rag": sum(1 for c in cases if c["suite"] == "rag"),
            "agent": sum(1 for c in cases if c["suite"] == "agent"),
            "multi": sum(1 for c in cases if c["suite"] == "multi"),
            "runnable": sum(1 for c in cases if c["runnable"]),
        },
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=1))
    print(f"wrote {OUT} — {payload['counts']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
