"""Shared pytest fixtures and suite parametrisation."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# The suites are written against the deterministic stub backend so that CI is
# reproducible. Set QTCAP_LLM_PROVIDER before running to target a real model.
os.environ.setdefault("QTCAP_LLM_PROVIDER", "stub")

from tests.runner.harness import load_cases, run_case  # noqa: E402


def pytest_addoption(parser):
    parser.addoption("--suite", default=None, help="run only 'blue' or 'red'")
    parser.addoption("--case-category", default=None, help="run only this category")


def _select(config, suite):
    cases = load_cases(suite)
    only = config.getoption("--case-category")
    if only:
        cases = [c for c in cases if c.get("category") == only]
    return cases


def pytest_generate_tests(metafunc):
    if "case" not in metafunc.fixturenames:
        return
    wanted = metafunc.config.getoption("--suite")
    suite = getattr(metafunc.module, "SUITE", None)
    if wanted and suite and wanted != suite:
        metafunc.parametrize("case", [], ids=[])
        return
    cases = _select(metafunc.config, suite)
    metafunc.parametrize("case", cases, ids=[c.get("id", "?") for c in cases])


@pytest.fixture(scope="session")
def results_bag():
    bag: list[dict] = []
    yield bag
    if bag:
        from tests.runner.report import write_reports

        write_reports(bag)


def assert_case(case, bag):
    result = run_case(case)
    bag.append(result)
    if not result["passed"]:
        lines = [f"{result['id']} — {result['title']}", f"  target: {result['target']}"]
        if result.get("error"):
            lines.append(f"  ERROR: {result['error']}")
        for c in result["checks"]:
            mark = "ok " if c["passed"] else "FAIL"
            lines.append(f"  [{mark}] {c['type']}: {c['message']}")
        answer = str(result.get("result", {}).get("answer", ""))[:400]
        if answer:
            lines.append(f"  answer: {answer}")
        pytest.fail("\n".join(lines), pytrace=False)
