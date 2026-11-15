# One-word commands for the common jobs. Run `make` to see them.
PY := .venv/bin/python

help:
	@echo "make setup     create .venv, install everything, install the browser for tests, turn on the privacy hooks"
	@echo "make run       start the dashboard with example data at http://localhost:8770/"
	@echo "make test      run all tests (server, statement readers, and the page in a browser)"
	@echo "make coverage  run the tests and report how much code they exercised"
	@echo "make shots     regenerate the README screenshots from example data"

.venv/bin/python:
	python3 -m venv .venv

setup: .venv/bin/python
	.venv/bin/pip install -q -r requirements-dev.txt
	$(PY) -m playwright install chromium
	sh tools/install-hooks.sh

run: .venv/bin/python
	.venv/bin/pip install -q -r requirements.txt
	$(PY) server.py

test: .venv/bin/python
	$(PY) -m pytest -q

coverage:
	sh tools/coverage.sh

shots:
	$(PY) tools/screenshots.py

.PHONY: help setup run test coverage shots
