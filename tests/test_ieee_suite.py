"""Guards on the IEEE 829 workbook harness.

These do not assert that the 317 cases pass. Most of the value in that suite is
in the cases that fail, and a gate demanding green would be closed by deleting
them. What is asserted here is that the harness itself is honest: every row is
bound, every binding runs, an unbound row is reported rather than skipped, and
the independent oracles are genuinely independent.

Run:
    pytest tests/test_ieee_suite.py -v
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

openpyxl = pytest.importorskip("openpyxl")
import yaml  # noqa: E402

from tests.ieee import oracles  # noqa: E402
from tests.ieee.executors import EXECUTORS  # noqa: E402

WORKBOOK = ROOT / "tests" / "ieee" / "Capital_Markets_GenAI_Agent_Test_Suite_IEEE.xlsx"
BINDINGS = ROOT / "tests" / "ieee" / "bindings.yaml"
SHEETS = ("GenAI Test Cases", "Agent Test Cases")


@pytest.fixture(scope="module")
def bindings() -> dict:
    return yaml.safe_load(BINDINGS.read_text())


@pytest.fixture(scope="module")
def case_ids() -> list[str]:
    wb = openpyxl.load_workbook(WORKBOOK, read_only=True)
    ids = []
    for sheet in SHEETS:
        ws = wb[sheet]
        for row in ws.iter_rows(min_row=2, max_col=1, values_only=True):
            if row[0]:
                ids.append(row[0])
    return ids


# ---------------------------------------------------------------------------
# Coverage
# ---------------------------------------------------------------------------
def test_the_workbook_still_holds_377_cases(case_ids):
    assert len(case_ids) == 377
    assert len(set(case_ids)) == 377, "duplicate Test Case IDs"


def test_every_workbook_row_has_an_execution_binding(case_ids, bindings):
    missing = [cid for cid in case_ids if cid not in bindings]
    assert not missing, f"{len(missing)} rows would run as Blocked: {missing[:8]}"


def test_no_binding_points_at_a_row_that_no_longer_exists(case_ids, bindings):
    orphans = sorted(set(bindings) - set(case_ids))
    assert not orphans, f"bindings with no row in the sheet: {orphans[:8]}"


def test_every_binding_names_a_real_executor(bindings):
    unknown = sorted({b["executor"] for b in bindings.values()} - set(EXECUTORS))
    assert not unknown, f"bindings reference executors that do not exist: {unknown}"


def test_every_capability_verdict_is_one_of_the_three(bindings):
    allowed = {"implemented", "partial", "absent"}
    bad = {cid: b["capability"] for cid, b in bindings.items() if b["capability"] not in allowed}
    assert not bad, bad


def test_the_suite_still_covers_every_requirement_area(bindings):
    """32 requirement areas, G01-G16 and A01-A16. Losing one silently is the risk."""
    areas = {cid.split("_")[2] for cid in bindings}
    expected = {f"G{i:02d}" for i in range(1, 17)} | {f"A{i:02d}" for i in range(1, 17)}
    assert areas == expected, f"missing: {sorted(expected - areas)}"


def test_the_capability_profile_has_not_silently_drifted(bindings):
    """A baseline, not a target.

    If someone relabels a pile of 'absent' cases as 'implemented' to make a
    report look better, this fails and asks them to say so out loud.
    """
    from collections import Counter

    counts = Counter(b["capability"] for b in bindings.values())
    assert counts["implemented"] == pytest.approx(219, abs=14)
    assert counts["absent"] == pytest.approx(99, abs=14)
    assert sum(counts.values()) == 377


# ---------------------------------------------------------------------------
# The harness runs
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("case_id", [
    "TC_G_G01_011",   # rag_query
    "TC_G_G03_028",   # no_fabrication
    "TC_G_G04_051",   # calculation against the oracle
    "TC_G_G05_058",   # guardrail_block
    "TC_G_G06_073",   # injection_block
    "TC_G_G08_098",   # persona_pair
    "TC_G_G09_108",   # conversation (expected to fail, must still run)
    "TC_G_G12_137",   # robustness
    "TC_A_A02_011",   # agent_tool
    "TC_A_A04_035",   # tool_contract
    "TC_A_A08_071",   # multi_agent
    "TC_A_A09_079",   # trace_audit
    "TC_G_G16_183",   # derivatives query correctness — the system's home ground
    "TC_A_A16_139",   # derivatives trading guardrail
])
def test_a_representative_case_from_each_executor_returns_a_verdict(case_id, bindings):
    outcome = EXECUTORS[bindings[case_id]["executor"]](dict(bindings[case_id]))
    assert outcome.status in {"Pass", "Fail", "Blocked"}
    assert outcome.actual, "every verdict must carry the observed result"


def test_a_failing_case_always_explains_itself(bindings):
    """A red row with an empty Remarks column is useless to whoever triages it."""
    binding = dict(bindings["TC_G_G09_108"])
    outcome = EXECUTORS[binding["executor"]](binding)
    assert outcome.status == "Fail"
    assert len(outcome.remark) > 40, "a failure must say why, not just that"


# ---------------------------------------------------------------------------
# The oracles are independent, which is the whole point of them
# ---------------------------------------------------------------------------
def test_the_oracle_module_does_not_import_the_application():
    source = (ROOT / "tests" / "ieee" / "oracles.py").read_text()
    assert "from app" not in source and "import app" not in source, (
        "the answer key must not be computed by the system under test"
    )


def test_black_scholes_oracle_matches_a_published_value():
    """S=100, K=100, r=5%, vol=20%, t=1 is the textbook case: 10.4506."""
    price = oracles.black_scholes(100, 100, 0.05, 0.20, 1.0, "call")
    assert price == pytest.approx(10.4506, abs=0.001)


def test_put_call_parity_holds_in_the_oracle():
    call = oracles.black_scholes(24800, 24800, 0.065, 0.14, 0.25, "call")
    put = oracles.black_scholes(24800, 24800, 0.065, 0.14, 0.25, "put")
    gap = oracles.put_call_parity_gap(call, put, 24800, 24800, 0.065, 0.25)
    assert abs(gap) < 1e-6


def test_cagr_and_compounding_agree_with_hand_arithmetic():
    assert oracles.cagr(100, 200, 10) == pytest.approx(0.071773, abs=1e-5)
    assert oracles.compound_interest(100000, 0.08, 2, 4) == pytest.approx(117165.94, abs=0.5)


def test_xirr_recovers_a_known_rate():
    flows = [(date(2024, 1, 1), -100000.0), (date(2025, 1, 1), 112000.0)]
    assert oracles.xirr(flows) == pytest.approx(0.12, abs=0.002)


def test_macaulay_duration_is_shorter_than_maturity_for_a_coupon_bond():
    duration = oracles.macaulay_duration(1000, 0.078, 0.0725, 5)
    assert 4.0 < duration < 5.0


# ---------------------------------------------------------------------------
# RAGAS proxies behave in the direction they claim
# ---------------------------------------------------------------------------
def test_faithfulness_falls_when_the_answer_leaves_the_context():
    from tests.ieee import ragas

    context = ["A NIFTY lot is 75 units and the contract expires on the last Thursday."]
    grounded = ragas.faithfulness("A NIFTY lot is 75 units, expiring the last Thursday.", context)
    invented = ragas.faithfulness("The Reserve Bank cut the repo rate by 40 basis points in "
                                  "March and inflation fell sharply thereafter.", context)
    assert grounded > invented


def test_harmfulness_catches_the_language_compliance_forbids():
    from tests.ieee import ragas

    assert ragas.harmfulness("This trade is a guaranteed profit and risk-free.") > 0
    assert ragas.harmfulness("Theta decays faster as expiry approaches.") == 0
