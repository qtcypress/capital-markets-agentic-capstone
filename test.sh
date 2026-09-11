#!/usr/bin/env bash
# Run the test suites. Usage: ./test.sh [blue|red|ui|all]
set -euo pipefail
cd "$(dirname "$0")"
WHAT="${1:-all}"
case "$WHAT" in
  blue) python3 -m pytest tests/test_blue_team.py -v ;;
  red)  python3 -m pytest tests/test_red_team.py -v ;;
  ui)   python3 -m pytest tests/test_ui.py -v ;;
  sec)  python3 -m pytest tests/test_hosting_security.py -v ;;
  fast) python3 tools/run_suite.py ;;
  all)  python3 -m pytest tests/test_blue_team.py tests/test_red_team.py tests/test_hosting_security.py -q
        echo; echo "Report: reports/test-report.html" ;;
  *)    echo "usage: ./test.sh [blue|red|ui|sec|fast|all]"; exit 1 ;;
esac
