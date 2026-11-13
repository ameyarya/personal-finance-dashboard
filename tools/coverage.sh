#!/bin/sh
# Run the whole test suite and report how much of the code it exercised (Python files and the page's JavaScript).
# Usage: sh tools/coverage.sh [pytest args]
cd "$(dirname "$0")/.." || exit 1
rm -f .coverage .coverage.* js-coverage.json
export COVERAGE_PROCESS_START="$PWD/.coveragerc"          # the servers the tests start are measured too
export JS_COVERAGE=1                                      # and the page's JavaScript
.venv/bin/python -m coverage run -m pytest -q "$@" || exit $?
.venv/bin/python -m coverage combine -q 2>/dev/null
.venv/bin/python -m coverage report --skip-covered | tail -25
node tools/js-coverage/report.js "$@" 2>/dev/null
