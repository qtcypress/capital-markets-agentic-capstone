"""Blue-team suite — the system behaves correctly on legitimate input.

    pytest tests/test_blue_team.py -v
    pytest tests/test_blue_team.py --case-category tool_selection
"""
from tests.conftest import assert_case

SUITE = "blue"


def test_blue_case(case, results_bag):
    assert_case(case, results_bag)
