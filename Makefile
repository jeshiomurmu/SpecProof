VENV := .venv
ifeq ($(OS),Windows_NT)
BIN := $(VENV)/Scripts
PYTHON ?= py -3.11
else
BIN := $(VENV)/bin
PYTHON ?= python3
endif

.PHONY: setup check test-e2e fetch pipeline eval guard

setup:
	$(PYTHON) -m venv $(VENV)
	$(BIN)/python -m pip install -e ".[dev]"
	$(BIN)/python -m pip freeze --exclude-editable > requirements.lock
	$(BIN)/pre-commit install

check:
	$(BIN)/ruff check .
	$(BIN)/ruff format --check .
	$(BIN)/mypy
	$(BIN)/pytest -m "unit or integration" --cov=specproof --cov-report=term-missing --cov-fail-under=85

test-e2e:
	$(BIN)/pytest -m "e2e or real_source"

fetch:
	$(BIN)/specproof fetch

pipeline:
	$(BIN)/specproof ingest
	$(BIN)/specproof segment
	$(BIN)/specproof verify --report-only
	$(BIN)/specproof classify
	$(BIN)/specproof export-openapi
	$(BIN)/specproof compare --community
	$(BIN)/specproof conform --client artifacts/work/py-unifi-access
	$(BIN)/specproof report

eval:
	$(BIN)/specproof eval

guard:
	$(BIN)/specproof guard
