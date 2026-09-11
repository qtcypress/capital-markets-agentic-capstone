"""Red-team suite — every case asserts that an attack FAILS.

    pytest tests/test_red_team.py -v
    pytest tests/test_red_team.py --case-category prompt_injection
"""
from tests.conftest import assert_case

SUITE = "red"


def test_red_case(case, results_bag):
    assert_case(case, results_bag)
