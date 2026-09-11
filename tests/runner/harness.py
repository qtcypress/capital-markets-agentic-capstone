"""Loads YAML test cases, executes them against a target, and runs the checks.

Targets
-------
  rag          RAG pipeline            -> answer, citations, contexts, grounding, guards
  agent        single tool-calling agent -> answer, tools_used, tool_calls, steps
  multi        MCP multi-agent system  -> answer, agents_used, mcp_calls, subtasks
  tool         direct tool invocation  -> ok, result, error
  mcp          direct MCP tools/call   -> ok, result, error, server
  kb           raw retrieval only      -> contexts, retrieval_scores
  math         pure derivatives function -> function output
  guard        guardrail unit check    -> input/output guard result

Adding a target is a small, self-contained function — one of the lab exercises.
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SUITE_DIR = ROOT / "tests" / "suites"

from app.agents.orchestrator import Orchestrator  # noqa: E402
from app.agents.single_agent import SingleAgent  # noqa: E402
from app.agents.tools import execute_tool  # noqa: E402
from app.config import get_config  # noqa: E402
from app.guardrails import check_input, check_output  # noqa: E402
from app.market import derivatives  # noqa: E402
from app.mcpsvc import MCPSession  # noqa: E402
from app.rag import get_pipeline, get_store  # noqa: E402

from .evaluators import run_check  # noqa: E402

VALID_TARGETS = {"rag", "agent", "multi", "tool", "mcp", "kb", "math", "guard"}
REQUIRED_FIELDS = {"id", "title", "target", "checks"}


# ---------------------------------------------------------------------------
# Case loading and validation
# ---------------------------------------------------------------------------
def load_cases(suite: str | None = None, directory: Path | None = None) -> list[dict[str, Any]]:
    directory = directory or SUITE_DIR
    roots = [directory / suite] if suite else [directory / "blue", directory / "red"]
    cases: list[dict[str, Any]] = []
    for root in roots:
        if not root.exists():
            continue
        for path in sorted(root.glob("*.yaml")) + sorted(root.glob("*.yml")):
            loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or []
            if not isinstance(loaded, list):
                raise ValueError(f"{path.name}: top level must be a list of cases")
            for case in loaded:
                case["_file"] = path.name
                case.setdefault("suite", root.name)
                cases.append(case)
    return cases


def validate_case(case: dict) -> list[str]:
    problems = []
    missing = REQUIRED_FIELDS - set(case)
    if missing:
        problems.append(f"missing fields: {sorted(missing)}")
    if case.get("target") not in VALID_TARGETS:
        problems.append(f"invalid target '{case.get('target')}' (valid: {sorted(VALID_TARGETS)})")
    if not isinstance(case.get("checks"), list) or not case.get("checks"):
        problems.append("checks must be a non-empty list")
    else:
        for i, chk in enumerate(case["checks"]):
            if not isinstance(chk, dict) or "type" not in chk:
                problems.append(f"check[{i}] must be an object with a 'type'")
    return problems


# ---------------------------------------------------------------------------
# Shared, lazily-created application instances
# ---------------------------------------------------------------------------
_shared: dict[str, Any] = {}


def _rag():
    if "rag" not in _shared:
        _shared["rag"] = get_pipeline()
    return _shared["rag"]


def _agent():
    if "agent" not in _shared:
        _shared["agent"] = SingleAgent()
    return _shared["agent"]


def _orch():
    if "orch" not in _shared:
        _shared["orch"] = Orchestrator(transport=os.environ.get("QTCAP_MCP_TRANSPORT", "in_process"))
    return _shared["orch"]


def _mcp():
    if "mcp" not in _shared:
        _shared["mcp"] = MCPSession.start(os.environ.get("QTCAP_MCP_TRANSPORT", "in_process"))
    return _shared["mcp"]


def reset_shared() -> None:
    for key in ("orch", "mcp"):
        obj = _shared.pop(key, None)
        if obj is not None:
            try:
                obj.close()
            except Exception:  # noqa: BLE001
                pass
    _shared.clear()


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------
def execute_case(case: dict) -> dict[str, Any]:
    """Run one case's target and return a normalised result dict."""
    target = case["target"]
    inp = case.get("input") or {}
    started = time.perf_counter()

    if target == "rag":
        res = _rag().answer(
            inp.get("query", ""),
            top_k=inp.get("top_k"),
            min_score=inp.get("min_score"),
            category=inp.get("category"),
        ).to_dict()

    elif target == "agent":
        res = _agent().run(inp.get("query", "")).to_dict()

    elif target == "multi":
        res = _orch().run(inp.get("query", "")).to_dict()

    elif target == "tool":
        res = execute_tool(inp.get("tool", ""), inp.get("arguments") or {})

    elif target == "mcp":
        record = _mcp().call(inp.get("tool", ""), inp.get("arguments") or {})
        res = {
            "ok": record.ok, "server": record.server, "tool": record.tool,
            "arguments": record.arguments, "result": record.result,
            "error": record.error, "transport": record.transport,
            "duration_ms": record.duration_ms,
        }

    elif target == "kb":
        hits = get_store().search(
            inp.get("query", ""),
            top_k=inp.get("top_k", 4),
            min_score=inp.get("min_score", 0.0),
            category=inp.get("category"),
        )
        res = {
            "contexts": [
                {"doc_id": h["chunk"].doc_id, "section": h["chunk"].section,
                 "score": h["score"], "rank": h["rank"], "category": h["chunk"].category,
                 "authority": h["chunk"].authority, "text": h["chunk"].text}
                for h in hits
            ],
            "retrieval_scores": [h["score"] for h in hits],
            "answer": " ".join(h["chunk"].text for h in hits),
        }

    elif target == "math":
        fn_name = inp.get("function", "")
        fn = getattr(derivatives, fn_name, None)
        if fn is None:
            res = {"ok": False, "error": {"code": "unknown_function", "message": fn_name}}
        else:
            try:
                out = fn(**(inp.get("arguments") or {}))
                res = {"ok": True, "result": out, "error": None}
            except Exception as exc:  # noqa: BLE001
                res = {"ok": False, "result": None,
                       "error": {"code": type(exc).__name__, "message": str(exc)}}

    elif target == "guard":
        direction = inp.get("direction", "input")
        text = inp.get("text", "")
        guard = check_input(text) if direction == "input" else check_output(text)
        res = {
            "answer": guard.sanitized_text or text,
            "refused": not guard.allowed,
            ("input_guard" if direction == "input" else "output_guard"): guard.to_dict(),
        }
        res.setdefault("input_guard", {})
        res.setdefault("output_guard", {})

    else:
        raise ValueError(f"unknown target '{target}'")

    res.setdefault("latency_ms", int((time.perf_counter() - started) * 1000))
    return res


def run_case(case: dict) -> dict[str, Any]:
    """Execute a case and evaluate every check. Never raises."""
    started = time.perf_counter()
    problems = validate_case(case)
    if problems:
        return {
            "id": case.get("id", "<no id>"), "title": case.get("title", ""),
            "suite": case.get("suite"), "category": case.get("category"),
            "severity": case.get("severity", "medium"), "target": case.get("target"),
            "passed": False, "checks": [], "error": "; ".join(problems),
            "duration_ms": 0, "result": {},
        }

    original_mode = os.environ.get("QTCAP_VULNERABLE_MODE")
    if case.get("vulnerable_mode") is not None:
        os.environ["QTCAP_VULNERABLE_MODE"] = "1" if case["vulnerable_mode"] else "0"
        get_config(refresh=True)

    error = None
    try:
        result = execute_case(case)
    except Exception as exc:  # noqa: BLE001
        result, error = {}, f"{type(exc).__name__}: {exc}"
    finally:
        if case.get("vulnerable_mode") is not None:
            if original_mode is None:
                os.environ.pop("QTCAP_VULNERABLE_MODE", None)
            else:
                os.environ["QTCAP_VULNERABLE_MODE"] = original_mode
            get_config(refresh=True)

    checks = [] if error else [run_check(spec, result) for spec in case["checks"]]
    return {
        "id": case["id"], "title": case["title"], "suite": case.get("suite"),
        "category": case.get("category", "uncategorised"),
        "severity": case.get("severity", "medium"), "target": case["target"],
        "tags": case.get("tags", []), "file": case.get("_file"),
        "input": case.get("input", {}),
        "passed": bool(checks) and all(c["passed"] for c in checks) and error is None,
        "checks": checks, "error": error,
        "duration_ms": int((time.perf_counter() - started) * 1000),
        "result": result,
    }


def summarise(results: list[dict]) -> dict[str, Any]:
    total = len(results)
    passed = sum(1 for r in results if r["passed"])
    by_cat: dict[str, dict[str, int]] = {}
    by_sev: dict[str, dict[str, int]] = {}
    for r in results:
        for bucket, key in ((by_cat, r["category"]), (by_sev, r["severity"])):
            entry = bucket.setdefault(key, {"total": 0, "passed": 0})
            entry["total"] += 1
            entry["passed"] += int(r["passed"])
    return {
        "total": total, "passed": passed, "failed": total - passed,
        "pass_rate": round(passed / total * 100, 1) if total else 0.0,
        "by_category": by_cat, "by_severity": by_sev,
        "total_duration_ms": sum(r["duration_ms"] for r in results),
        "failures": [
            {"id": r["id"], "title": r["title"], "severity": r["severity"],
             "reasons": [f"{c['type']}: {c['message']}" for c in r["checks"] if not c["passed"]]
                        or [r.get("error") or "unknown"]}
            for r in results if not r["passed"]
        ],
    }
