"""Execute the IEEE 829 workbook and write the results back into it.

    python tools/run_ieee_suite.py                       # run everything
    python tools/run_ieee_suite.py --category G06        # one category
    python tools/run_ieee_suite.py --id TC_G_G04_046     # one case
    python tools/run_ieee_suite.py --fast                # skip the load and latency cases
    python tools/run_ieee_suite.py --file-findings       # also file each failure in the console

The input workbook is never modified. The run produces
`reports/ieee/<name>-executed.xlsx` with four columns filled in on every row —
Status, Actual Result, Defects, Remarks — plus two new sheets:

  Execution Summary   pass rate by category, and by capability verdict
  Defect Register     one row per distinct defect, with the cases that prove it

Why failures are expected
-------------------------
The workbook was written against two products that do not exist. Bound to a real
system, some of its requirements land on capabilities this system genuinely does
not have — conversation memory, human approval gates, an order lifecycle. Those
cases fail, and the failure is the deliverable: a requirement with no
implementation behind it is a finding, not a test to delete. The summary counts
them separately from defects in code, because a triage meeting has to tell those
two apart.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import traceback
from collections import Counter, defaultdict
from copy import copy
from pathlib import Path

import openpyxl
import yaml
from openpyxl.styles import Alignment, Font, PatternFill

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.ieee.executors import EXECUTORS, Outcome  # noqa: E402

BINDINGS = ROOT / "tests" / "ieee" / "bindings.yaml"
DEFAULT_WORKBOOK = ROOT / "tests" / "ieee" / "Capital_Markets_GenAI_Agent_Test_Suite_IEEE.xlsx"
REPORTS = ROOT / "reports" / "ieee"

CASE_SHEETS = ("GenAI Test Cases", "Agent Test Cases")
COL = {"id": 1, "category": 2, "requirement": 3, "objective": 4, "preconditions": 5,
       "data": 6, "steps": 7, "expected": 8, "special": 9, "depends": 10, "priority": 11,
       "type": 12, "status": 13, "actual": 14, "defects": 15, "remarks": 16}

FILL = {
    "Pass": PatternFill("solid", fgColor="D6F0DC"),
    "Fail": PatternFill("solid", fgColor="FBD9DC"),
    "Fail (expected)": PatternFill("solid", fgColor="FDECC8"),
    "Blocked": PatternFill("solid", fgColor="E3E6EC"),
}

SLOW_EXECUTORS = {"latency", "concurrency"}

# Which application each executor drives. The workbook is organised by
# requirement area; a tester working on the RAG pipeline wants it organised by
# what they can actually run against, which is what the two "Applicable" sheets
# do. A case can legitimately touch both — the multi-agent supervisor calls the
# knowledge base through MCP — so the mapping allows two targets.
TARGETS = {
    "rag_query": ("RAG",), "rag_refusal": ("RAG",), "no_fabrication": ("RAG",),
    "ragas_metric": ("RAG",), "citation_check": ("RAG",), "persona_pair": ("RAG",),
    "style_check": ("RAG",), "conversation": ("RAG",), "localisation": ("RAG",),
    "robustness": ("RAG",), "latency": ("RAG",), "guardrail_block": ("RAG",),
    "injection_block": ("RAG",), "leakage_block": ("RAG",),
    "agent_tool": ("Agent",), "agent_tool_error": ("Agent",), "agent_plan": ("Agent",),
    "agent_react": ("Agent",), "agent_state": ("Agent",), "approval_gate": ("Agent",),
    "autonomy_boundary": ("Agent",), "agent_redteam": ("Agent",), "escalation": ("Agent",),
    "e2e_scenario": ("Agent",), "trace_audit": ("Agent",), "tool_contract": ("Agent",),
    "calculation": ("Agent",), "market_feed": ("Agent",),
    "multi_agent": ("Agent", "RAG"), "concurrency": ("Agent", "RAG"),
    "blue_team": ("RAG", "Agent"), "regression": ("RAG", "Agent"),
}


def targets_for(executor: str) -> tuple[str, ...]:
    return TARGETS.get(executor, ("Agent",))

# ---------------------------------------------------------------------------
# Defect register: distinct causes, not one row per failing case
# ---------------------------------------------------------------------------
DEFECTS = {
    "DEF-001": dict(
        title="No conversation state: every request is independent",
        severity="High", area="RAG pipeline / API",
        detail="There is no session id, no message history and no memory store, so nothing a user "
               "says in one turn is available in the next. Pronouns, corrections and stated "
               "preferences are all lost.",
        fix="Add a session id, a bounded per-session history, and a decision about what is safe to "
            "carry forward. Then decide what must NOT be carried — a stated risk profile is not the "
            "same kind of state as a pronoun referent."),
    "DEF-002": dict(
        title="No human-in-the-loop approval model",
        severity="High", area="Agent",
        detail="Tool authorisation exists, but there is no approver role, no pending-approval "
               "object, no timeout and no decision log. Requests are refused because the system "
               "cannot trade, which is not the same as a gate holding.",
        fix="Model an approval as a first-class object with states and a timeout, and test the "
            "timeout path before the happy path."),
    "DEF-003": dict(
        title="Non-English input is neither answered nor explicitly declined",
        severity="Medium", area="Guardrails / RAG",
        detail="The corpus, the scope classifier and every guardrail pattern are English-only. A "
               "Hindi or Tamil question is treated as out of scope by accident rather than handled "
               "as a language the system does not support.",
        fix="Detect the script, and answer with an explicit 'this assistant works in English' "
            "message. Then decide whether the guardrails are safe against a translated attack."),
    "DEF-004": dict(
        title="No trace persistence, so no audit trail",
        severity="High", area="Observability",
        detail="Traces are returned in the HTTP response and never stored. Nothing can be "
               "reconstructed after the fact, there is no retention period, and tamper-evidence is "
               "not applicable because there is nothing to tamper with.",
        fix="Persist traces with a correlation id and a retention policy before claiming any "
            "regulated use."),
    "DEF-005": dict(
        title="No transactional lifecycle (orders, holdings, confirmations)",
        severity="Medium", area="Agent",
        detail="The workbook's end-to-end scenarios assume an order management system, a portfolio "
               "store and confirmations. This assistant deliberately has none.",
        fix="Either descope these requirements or build the lifecycle. Do not let the agent narrate "
            "steps it cannot perform."),
    "DEF-006": dict(
        title="Unknown symbols return a generated quote instead of an error",
        severity="High", area="Market data tools",
        detail="get_quote on an unresolvable ticker returns ok=true with a synthetic payload. The "
               "provenance field says 'synthetic', but a caller that does not read it — including "
               "the agent's own answer — presents an invented price as a real one.",
        fix="Fail closed on symbols outside the contract master, and make the answer layer refuse "
            "to quote a synthetic payload as a price."),
    "DEF-007": dict(
        title="No aggregation or alerting across requests",
        severity="Medium", area="Blue team",
        detail="Guardrail hits are counted per request and then discarded. Fifty injection attempts "
               "from one client look exactly like fifty unrelated requests.",
        fix="Aggregate control triggers per client over a window, and alert above a threshold."),
    "DEF-008": dict(
        title="No financial calculators beyond derivatives pricing",
        severity="Medium", area="Tools",
        detail="CAGR, XIRR, bond duration, portfolio return, Sharpe and tax arithmetic have no tool "
               "behind them. The requirement set assumes a general financial calculator.",
        fix="Either add the calculators with tested oracles, or descope — but do not let the model "
            "attempt the arithmetic unaided."),
    "DEF-009": dict(
        title="RAGAS-style metric below its release threshold",
        severity="Medium", area="RAG pipeline",
        detail="One or more retrieval/response metrics scores under the agreed threshold on the "
               "version-controlled benchmark set.",
        fix="Read the per-question scores first. A single bad question can sink a mean, and the "
            "lexical proxy is weaker than an LLM judge on paraphrase."),
    "DEF-010": dict(
        title="No streaming, cache tier, canary or priority queue",
        severity="Low", area="Platform",
        detail="Several performance and rollout requirements assume infrastructure this single-"
               "process deployment does not have.",
        fix="Descope, or record them as architectural prerequisites rather than test failures."),
    "DEF-011": dict(
        title="Answer register does not change when the user asks for simpler or more technical",
        severity="Low", area="RAG pipeline",
        detail="'Explain gamma simply' and 'explain gamma technically' produce the same answer.",
        fix="Pass the requested register into the prompt, and test that the two answers actually "
            "differ."),
    "DEF-012": dict(
        title="Out-of-corpus question answered instead of refused",
        severity="High", area="RAG pipeline",
        detail="A question the corpus cannot support produced an answer rather than a grounded "
               "refusal. This is the failure mode that puts a wrong number in front of a client.",
        fix="Raise the retrieval floor, or add an explicit 'is this answerable from what I "
            "retrieved' check before generation."),
    "DEF-013": dict(
        title="Guardrail did not fire on an adversarial prompt",
        severity="High", area="Guardrails",
        detail="A red-team prompt was neither blocked nor safely redirected. The controls are "
               "pattern-based, and this phrasing is outside the patterns.",
        fix="Add the pattern, then ask what else it does not cover — every pattern you add is "
            "evidence the approach has a ceiling."),
    "DEF-014": dict(
        title="Latency over budget",
        severity="Medium", area="Platform",
        detail="A response exceeded its stated budget, most often under concurrency: one worker "
               "serves requests in turn.",
        fix="Measure before tuning. Decide whether the budget or the deployment is wrong."),
    "DEF-017": dict(
        title="No plan object: the agent chooses one tool per turn",
        severity="Medium", area="Agent",
        detail="Nothing in the response represents an ordered plan, so a decomposition cannot be "
               "inspected, replayed or corrected. The supervisor splits compound requests, but the "
               "single agent does not plan at all.",
        fix="Emit the plan as data before executing it, and test the plan separately from the "
            "execution — most planning defects are invisible once the answer is written."),
    "DEF-018": dict(
        title="No escalation path to a human",
        severity="Medium", area="Agent",
        detail="Failures are handled and reported, but nothing escalates: no confidence score, no "
               "queue, no ticket, no notification, and no statement to the user that they are "
               "talking to software rather than an adviser.",
        fix="Decide the escalation trigger first (confidence, repeated tool failure, a flagged "
            "client), then build the queue. A trigger with nowhere to send the case is worse than "
            "none."),
    "DEF-019": dict(
        title="Fairness: the answer moves with an attribute that should not matter",
        severity="Medium", area="RAG pipeline",
        detail="Paired personas differing only in age, stated accessibility need or implied "
               "socioeconomic status retrieved different passages and produced different answers.",
        fix="Look at retrieval before generation — the persona text is entering the query and "
            "changing what comes back, which is a retrieval bug wearing a fairness costume."),
    "DEF-020": dict(
        title="Multi-agent routing and duplicate-call gaps",
        severity="Medium", area="Multi-agent",
        detail="A two-part question was routed to one specialist; a repeated question produced two "
               "identical MCP calls; a request needing a compliance veto was processed by the "
               "supervisor rather than vetoed.",
        fix="Test the router separately from the specialists. Duplicate suppression belongs in the "
            "supervisor, not in each specialist."),
    "DEF-016": dict(
        title="Agent picks the right tool then fails to extract its required arguments",
        severity="High", area="Agent",
        detail="On a well-formed question the agent selected the correct tool, omitted a required "
               "argument, and returned the raw tool error to the user as the answer.",
        fix="Two defects in one: argument extraction, and an answer layer that prints internal "
            "error envelopes. Fix the second first — it is the one a client would see."),
    "DEF-015": dict(
        title="No multi-provider reconciliation for market data",
        severity="Low", area="Market data",
        detail="Two providers exist but are chained as fallbacks, never compared. A wrong price "
               "from the primary is never contradicted.",
        fix="Read both and compare when the value matters."),
}

# Which defect a failing case belongs to, decided by executor and capability.
DEFECT_ROUTING = [
    (lambda b, o: b["executor"] == "agent_plan", "DEF-017"),
    (lambda b, o: b["executor"] == "escalation", "DEF-018"),
    (lambda b, o: b["executor"] == "persona_pair", "DEF-019"),
    (lambda b, o: b["executor"] == "multi_agent", "DEF-020"),
    (lambda b, o: b["executor"] in {"agent_tool", "agent_react"}, "DEF-017"),
    (lambda b, o: b["executor"] == "rag_query", "DEF-012"),
    (lambda b, o: b["executor"] == "conversation", "DEF-001"),
    (lambda b, o: b["executor"] == "agent_state", "DEF-001"),
    (lambda b, o: b["executor"] == "approval_gate", "DEF-002"),
    (lambda b, o: b["executor"] == "localisation", "DEF-003"),
    (lambda b, o: b["executor"] == "trace_audit", "DEF-004"),
    (lambda b, o: b["executor"] == "e2e_scenario", "DEF-005"),
    (lambda b, o: b["executor"] in {"agent_tool_error", "tool_contract"}
     and "synthetic" in json.dumps(o.evidence), "DEF-006"),
    (lambda b, o: b["executor"] == "blue_team", "DEF-007"),
    (lambda b, o: b["executor"] == "calculation"
     and o.evidence.get("argument_extraction_failed"), "DEF-016"),
    (lambda b, o: b["executor"] == "calculation", "DEF-008"),
    (lambda b, o: b["executor"] == "ragas_metric", "DEF-009"),
    (lambda b, o: b["executor"] in {"latency", "concurrency"} and b["capability"] == "absent",
     "DEF-010"),
    (lambda b, o: b["executor"] == "style_check", "DEF-011"),
    (lambda b, o: b["executor"] in {"rag_refusal", "no_fabrication", "citation_check"}, "DEF-012"),
    (lambda b, o: b["executor"] in {"guardrail_block", "injection_block", "leakage_block",
                                    "agent_redteam", "autonomy_boundary"}, "DEF-013"),
    (lambda b, o: b["executor"] in {"latency", "concurrency"}, "DEF-014"),
    (lambda b, o: b["executor"] == "market_feed", "DEF-015"),
]


def route_defect(binding: dict, outcome: Outcome) -> str:
    for predicate, defect in DEFECT_ROUTING:
        try:
            if predicate(binding, outcome):
                return defect
        except Exception:  # noqa: BLE001
            continue
    return "DEF-005"


# ---------------------------------------------------------------------------
def load_bindings() -> dict:
    return yaml.safe_load(BINDINGS.read_text())


def execute(case_id: str, binding: dict) -> tuple[Outcome, float]:
    executor = EXECUTORS[binding["executor"]]
    payload = dict(binding)
    started = time.perf_counter()
    try:
        outcome = executor(payload)
    except Exception as exc:  # noqa: BLE001
        outcome = Outcome(
            "Fail", f"{type(exc).__name__}: {exc}",
            {"traceback": traceback.format_exc(limit=4).splitlines()[-3:]},
            "The case raised an unhandled exception. That is a result, not a broken test — read the "
            "traceback before assuming the harness is at fault.",
        )
    return outcome, (time.perf_counter() - started) * 1000


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--workbook", default=str(DEFAULT_WORKBOOK))
    parser.add_argument("--out", default=None)
    parser.add_argument("--category", help="e.g. G06 or A02")
    parser.add_argument("--id", dest="case_id")
    parser.add_argument("--fast", action="store_true", help="skip load and latency cases")
    parser.add_argument("--file-findings", action="store_true",
                        help="also file each distinct defect in the console's findings store")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    workbook_path = Path(args.workbook)
    if not workbook_path.exists():
        print(f"Workbook not found: {workbook_path}", file=sys.stderr)
        return 2

    bindings = load_bindings()
    wb = openpyxl.load_workbook(workbook_path)

    selected: list[tuple[str, str, int]] = []          # (sheet, case id, row)
    for sheet_name in CASE_SHEETS:
        ws = wb[sheet_name]
        for row in range(2, ws.max_row + 1):
            case_id = ws.cell(row, COL["id"]).value
            if not case_id:
                continue
            if args.case_id and case_id != args.case_id:
                continue
            if args.category and f"_{args.category}_" not in case_id:
                continue
            selected.append((sheet_name, case_id, row))

    if not selected:
        print("Nothing selected.", file=sys.stderr)
        return 2

    results: dict[str, dict] = {}
    counts: Counter = Counter()
    by_category: dict[str, Counter] = defaultdict(Counter)
    defect_cases: dict[str, list[str]] = defaultdict(list)
    started = time.perf_counter()

    for index, (sheet_name, case_id, row) in enumerate(selected, start=1):
        binding = bindings.get(case_id)
        ws = wb[sheet_name]
        category = (ws.cell(row, COL["category"]).value or "?").split(" - ")[0]

        if binding is None:
            outcome, elapsed = Outcome("Blocked", "No execution binding exists for this case.", {},
                                       "Add it to tests/ieee/bindings.yaml."), 0.0
            capability = "unbound"
        elif args.fast and binding["executor"] in SLOW_EXECUTORS:
            outcome, elapsed = Outcome("Blocked", "Skipped by --fast.", {}, ""), 0.0
            capability = binding["capability"]
        else:
            outcome, elapsed = execute(case_id, binding)
            capability = binding["capability"]

        status = outcome.status
        expected_failure = status == "Fail" and capability == "absent"
        display = "Fail (expected)" if expected_failure else status

        defect = ""
        if status == "Fail" and binding is not None:
            defect = route_defect(binding, outcome)
            defect_cases[defect].append(case_id)

        results[case_id] = dict(sheet=sheet_name, row=row, status=display, outcome=outcome,
                                capability=capability, defect=defect, elapsed_ms=elapsed,
                                category=category)
        counts[display] += 1
        by_category[category][display] += 1

        if not args.quiet:
            mark = {"Pass": "PASS", "Fail": "FAIL", "Fail (expected)": "GAP ", "Blocked": "BLOK"}[display]
            print(f"[{index:3}/{len(selected)}] {mark} {case_id}  {outcome.actual[:72]}")

    elapsed_total = time.perf_counter() - started

    # -- write the results back into the sheet ------------------------------
    for case_id, record in results.items():
        ws = wb[record["sheet"]]
        row, outcome = record["row"], record["outcome"]
        ws.cell(row, COL["status"]).value = record["status"]
        ws.cell(row, COL["status"]).fill = FILL[record["status"]]
        evidence = json.dumps(outcome.evidence, default=str, sort_keys=True)
        ws.cell(row, COL["actual"]).value = f"{outcome.actual}\n\nEvidence: {evidence[:900]}"
        ws.cell(row, COL["actual"]).alignment = Alignment(wrap_text=True, vertical="top")
        ws.cell(row, COL["defects"]).value = record["defect"]
        remark = outcome.remark
        binding = bindings.get(case_id) or {}
        if binding.get("note"):
            remark = f"{remark} | Binding: {binding['note']}" if remark else binding["note"]
        remark = f"[{record['capability']}] {remark}".strip()
        ws.cell(row, COL["remarks"]).value = remark[:1200]
        ws.cell(row, COL["remarks"]).alignment = Alignment(wrap_text=True, vertical="top")

    _write_summary(wb, counts, by_category, defect_cases, elapsed_total, len(selected))
    _write_defect_register(wb, defect_cases)
    _write_applicable(wb, "RAG", results, bindings)
    _write_applicable(wb, "Agent", results, bindings)

    out_path = Path(args.out) if args.out else REPORTS / f"{workbook_path.stem}-executed.xlsx"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(out_path)

    if args.file_findings:
        _file_findings(defect_cases)

    print()
    print(f"  {counts['Pass']} passed · {counts['Fail']} failed · "
          f"{counts['Fail (expected)']} capability gaps · {counts['Blocked']} blocked "
          f"of {len(selected)} in {elapsed_total:.0f}s")
    print(f"  executed workbook: {out_path}")
    executed = len(selected) - counts["Blocked"]
    if executed:
        print(f"  pass rate (excluding blocked): {counts['Pass'] / executed:.1%}")
    return 0


def _write_summary(wb, counts, by_category, defect_cases, elapsed, total) -> None:
    if "Execution Summary" in wb.sheetnames:
        del wb["Execution Summary"]
    ws = wb.create_sheet("Execution Summary", 0)
    bold = Font(bold=True)

    ws["A1"], ws["A1"].font = "Execution Summary", Font(bold=True, size=14)
    ws["A2"] = f"System under test: Capital Markets Agentic Capstone (RAG + single agent + MCP "
    ws["A3"] = f"multi-agent). Executed {total} of 317 cases in {elapsed:.0f} seconds."
    ws["A4"] = ("A 'capability gap' is a case bound to a requirement this system has no "
                "implementation for. It is a finding about the product, not a bug in the code.")
    for row in ("A2", "A3", "A4"):
        ws[row].alignment = Alignment(wrap_text=True)

    ws.append([])
    ws.append(["Verdict", "Cases", "Share"])
    for cell in ws[ws.max_row]:
        cell.font = bold
    for verdict in ("Pass", "Fail", "Fail (expected)", "Blocked"):
        n = counts.get(verdict, 0)
        ws.append([verdict, n, f"{n / total:.1%}" if total else "—"])
        ws.cell(ws.max_row, 1).fill = FILL[verdict]

    ws.append([])
    ws.append(["Category", "Pass", "Fail", "Capability gap", "Blocked", "Pass rate"])
    for cell in ws[ws.max_row]:
        cell.font = bold
    for category in sorted(by_category):
        c = by_category[category]
        executed = sum(c.values()) - c.get("Blocked", 0)
        ws.append([category, c.get("Pass", 0), c.get("Fail", 0), c.get("Fail (expected)", 0),
                   c.get("Blocked", 0),
                   f"{c.get('Pass', 0) / executed:.0%}" if executed else "—"])

    ws.append([])
    ws.append(["Defect", "Title", "Severity", "Cases proving it"])
    for cell in ws[ws.max_row]:
        cell.font = bold
    for defect, cases in sorted(defect_cases.items(), key=lambda kv: -len(kv[1])):
        meta = DEFECTS.get(defect, {})
        ws.append([defect, meta.get("title", ""), meta.get("severity", ""), len(cases)])

    for column, width in (("A", 22), ("B", 46), ("C", 16), ("D", 18), ("E", 12), ("F", 12)):
        ws.column_dimensions[column].width = width


def _write_applicable(wb, target: str, results, bindings) -> None:
    """One sheet per application: every case that actually exercises it.

    The workbook's own sheets split by requirement area, which is the right shape
    for traceability and the wrong one for a tester who has been handed the RAG
    pipeline and needs to know what to run. These two sheets answer that.
    """
    name = f"{target} Applicable"
    if name in wb.sheetnames:
        del wb[name]
    ws = wb.create_sheet(name, 2)
    bold = Font(bold=True)

    rows = [(cid, r) for cid, r in results.items()
            if target in targets_for((bindings.get(cid) or {}).get("executor", ""))]
    verdicts = Counter(r["status"] for _, r in rows)
    executed = len(rows) - verdicts.get("Blocked", 0)

    ws["A1"] = f"Tests applicable to the {target} application"
    ws["A1"].font = Font(bold=True, size=14)
    ws["A2"] = (f"{len(rows)} of {len(results)} cases in the workbook exercise the "
                f"{target.lower()} path. {verdicts.get('Pass', 0)} pass, "
                f"{verdicts.get('Fail', 0)} fail, "
                f"{verdicts.get('Fail (expected)', 0)} are capability gaps, "
                f"{verdicts.get('Blocked', 0)} blocked"
                + (f" ({verdicts.get('Pass', 0) / executed:.0%} pass rate)." if executed else "."))
    ws["A2"].alignment = Alignment(wrap_text=True)
    ws["A3"] = ("A case appears here when the executor it is bound to drives this application. "
                "Cases bound to the supervisor, the rate limiter or a regression probe appear on "
                "both sheets, because they exercise both.")
    ws["A3"].alignment = Alignment(wrap_text=True)

    ws.append([])
    header = ["Test Case ID", "Category", "Executor", "Capability", "Status", "Defect",
              "What was sent", "What came back", "Why"]
    ws.append(header)
    for cell in ws[ws.max_row]:
        cell.font = bold

    order = {"Fail": 0, "Fail (expected)": 1, "Blocked": 2, "Pass": 3}
    for cid, record in sorted(rows, key=lambda kv: (order.get(kv[1]["status"], 9), kv[0])):
        binding = bindings.get(cid) or {}
        sent = binding.get("input") or binding.get("scenario") or binding.get("behaviour") \
            or binding.get("metric") or binding.get("gate") or binding.get("mode") or ""
        ws.append([cid, record["category"], binding.get("executor", ""), record["capability"],
                   record["status"], record["defect"], str(sent)[:400],
                   record["outcome"].actual[:400], record["outcome"].remark[:400]])
        ws.cell(ws.max_row, 5).fill = FILL[record["status"]]

    for column, width in (("A", 17), ("B", 10), ("C", 19), ("D", 13), ("E", 15), ("F", 10),
                          ("G", 52), ("H", 60), ("I", 60)):
        ws.column_dimensions[column].width = width
    for row in ws.iter_rows(min_row=6):
        for cell in row:
            cell.alignment = Alignment(wrap_text=True, vertical="top")
    ws.freeze_panes = "A6"


def _write_defect_register(wb, defect_cases) -> None:
    if "Defect Register" in wb.sheetnames:
        del wb["Defect Register"]
    ws = wb.create_sheet("Defect Register", 1)
    headers = ["Defect ID", "Title", "Severity", "Area", "What was observed",
               "Suggested direction", "Cases", "Test Case IDs"]
    ws.append(headers)
    for cell in ws[1]:
        cell.font = Font(bold=True)
    for defect, cases in sorted(defect_cases.items()):
        meta = DEFECTS.get(defect, {})
        ws.append([defect, meta.get("title", ""), meta.get("severity", ""), meta.get("area", ""),
                   meta.get("detail", ""), meta.get("fix", ""), len(cases),
                   ", ".join(sorted(cases))])
    for column, width in (("A", 12), ("B", 44), ("C", 10), ("D", 20), ("E", 64), ("F", 60),
                          ("G", 8), ("H", 70)):
        ws.column_dimensions[column].width = width
    for row in ws.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = Alignment(wrap_text=True, vertical="top")


def _file_findings(defect_cases) -> None:
    from app.issues import create_issue

    for defect, cases in sorted(defect_cases.items()):
        meta = DEFECTS.get(defect, {})
        create_issue(
            title=f"{defect} — {meta.get('title', 'unclassified')}",
            severity={"High": "high", "Medium": "medium", "Low": "low"}.get(
                meta.get("severity", "Medium"), "medium"),
            area=meta.get("area", "unknown"),
            impact=meta.get("detail", ""),
            steps="IEEE cases: " + ", ".join(sorted(cases)[:20]),
            reporter="ieee-runner",
        )
    print(f"  filed {len(defect_cases)} findings in the console")


if __name__ == "__main__":
    sys.exit(main())
