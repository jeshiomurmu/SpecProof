VENV := .venv
ifeq ($(OS),Windows_NT)
BIN := $(VENV)/Scripts
PYTHON ?= py -3.11
else
BIN := $(VENV)/bin
PYTHON ?= python3
endif

.PHONY: setup check test-e2e fetch pipeline eval guard site

setup:
	$(PYTHON) -m venv $(VENV)
	$(BIN)/python -m pip install -e ".[dev]"
	$(BIN)/python -m pip freeze --exclude-editable > requirements.lock
	$(BIN)/pre-commit install

check:
	$(BIN)/ruff check .
	$(BIN)/ruff format --check .
	$(BIN)/mypy
	$(BIN)/pytest -m "unit or integration" --cov=specproof --cov-report=term-missing --cov-report=json:artifacts/work/coverage.json --cov-fail-under=85

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
	$(BIN)/specproof conform --client artifacts/work/py-unifi-access $(if $(REPLAY_PYTHON),--python $(REPLAY_PYTHON))
	$(BIN)/specproof report

eval:
	$(BIN)/specproof eval

guard:
	$(BIN)/specproof guard

site:
	$(BIN)/python -c "import shutil; shutil.rmtree('dist/site', ignore_errors=True); shutil.copytree('artifacts/report', 'dist/site/report'); shutil.copyfile('demo/index.html', 'dist/site/index.html')"
