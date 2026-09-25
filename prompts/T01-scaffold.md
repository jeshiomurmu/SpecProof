# T01: Scaffold package, tooling and CI

Est. 45 min · Modes: Plan → Agent · Tests: CLI-001, GOV-005 · Bobcoin tier: Engine
Pre-flight: `git rev-parse HEAD > .specproof_task_base` (no `make check` yet; nothing exists)

## P: Plan mode
```text
Task T01 (SpecProof). Read AGENTS.md, docs/TECHNICAL_ARCHITECTURE.md sections 10, 11 and 12,
docs/TEST_PLAN.md sections 1, 2 and rows CLI-001 and GOV-005.
Produce a plan of at most 15 lines: files to create, dependencies you will pin, Makefile targets,
the two tests you will write first. Do not create or edit files.
```

## A: Agent mode
```text
ROLE
You are the lead engineer on SpecProof inside IBM Bob 2.0. AGENTS.md and .bob/rules/ are binding.

TASK
T01: create the Python package skeleton, tooling, and CI. Stubs only; no product logic.

READ FIRST
AGENTS.md; docs/TECHNICAL_ARCHITECTURE.md sections 10-12; docs/TEST_PLAN.md sections 1-2.

DELIVERABLES
1. pyproject.toml
   - [project]: name "specproof", version "0.1.0", requires-python ">=3.11", license "MIT",
     readme "README.md".
   - dependencies: typer>=0.12, pydantic>=2.7, jsonschema>=4.22, pdfplumber>=0.11,
     rapidfuzz>=3.9, pyyaml>=6.0, jinja2>=3.1, openapi-spec-validator>=0.7
   - optional-dependencies.dev: pytest>=8, pytest-cov>=5, hypothesis>=6.100, reportlab>=4.2,
     ruff>=0.6, mypy>=1.11, types-PyYAML, pre-commit>=3.7
   - [project.scripts] specproof = "specproof.cli:app"
   - src layout: [tool.setuptools.packages.find] where = ["src"]; include package data
     "specproof/report/templates/*.j2".
   - [tool.ruff] line-length = 100, target-version = "py311";
     [tool.ruff.lint] select = ["E","F","I","B","UP","SIM","RUF"].
   - [tool.mypy] strict = true, files = ["src"], plugins = ["pydantic.mypy"].
   - [tool.pytest.ini_options] testpaths = ["tests"], addopts = "-ra --strict-markers",
     markers = unit, integration, e2e, real_source (each with a one-line description).
   - [tool.coverage.run] source = ["specproof"], omit = ["*/specproof/cli.py"].
2. Makefile (GNU make; must also work in Git Bash on Windows):
   - VENV := .venv; BIN := $(VENV)/bin; on Windows_NT, BIN := $(VENV)/Scripts
   - setup:    python -m venv .venv; $(BIN)/pip install -e ".[dev]";
               $(BIN)/pip freeze --exclude-editable > requirements.lock; $(BIN)/pre-commit install
   - check:    ruff check . ; ruff format --check . ; mypy ;
               pytest -m "unit or integration" --cov=specproof --cov-report=term-missing
               --cov-fail-under=85
   - test-e2e: pytest -m "e2e or real_source"
   - fetch:    specproof fetch
   - pipeline: specproof ingest; segment; verify --report-only; classify; export-openapi;
               compare --community; conform --client artifacts/work/py-unifi-access; report
   - eval:     specproof eval
   - guard:    specproof guard
   - Mark all targets .PHONY. Every command runs from $(BIN).
3. src/specproof/__init__.py with __version__ = "0.1.0".
4. src/specproof/cli.py: a Typer app with EVERY command from architecture section 10
   (fetch, ingest, segment, verify, loop-status, classify, export-openapi, compare, conform,
   report, eval, audit-sample, audit-score, guard). Each is a stub that logs "not implemented
   (T0X)" and exits 0. Include the documented options as typed parameters now, so later tasks
   only fill in bodies. verify must also accept --report-only (always exit 0; used by make
   pipeline).
5. Empty packages with __init__.py: models, sources, ingest, util, verify, loop, compare,
   conformance, report (with report/templates/.gitkeep).
6. tests/conftest.py:
   - a pytest_collection_modifyitems hook that skips tests marked real_source when
     artifacts/work/spec.pdf does not exist (reason "run `make fetch` first");
   - a `repo_root` fixture.
7. tests/unit/test_cli.py::test_CLI_001_help_lists_all_commands: typer.testing.CliRunner,
   invoke --help, assert each of the 14 command names appears.
8. tests/unit/test_governance.py::test_GOV_005_gitleaks_hook_present: parse
   .pre-commit-config.yaml with yaml.safe_load and assert a hook with id "gitleaks" exists.
9. .pre-commit-config.yaml: astral-sh/ruff-pre-commit (ruff, ruff-format),
   gitleaks/gitleaks (id gitleaks), and a local mypy hook running `mypy` (language: system).
10. .github/workflows/ci.yml: on push and pull_request; ubuntu-latest; Python 3.11;
    apt-get install poppler-utils; make setup; make check.
11. LICENSE (MIT, year 2026, holder "Jeshio"). Append one line to docs/CHANGELOG.md.

METHOD
1. Write the two tests first. Run pytest and confirm they fail (the CLI or config is missing).
2. Create the files. Run `make setup`, then `make check`.
3. Fix until green. Do not lower --cov-fail-under.

CONSTRAINTS
- No product logic in any stub. No network access except pip installs.
- Do not modify docs/ (except the CHANGELOG line), .bob/, sources/, eval/, or prompts/.

ACCEPTANCE CRITERIA
- `make setup` completes; `make check` exits 0. Paste its final 5 lines verbatim.
- `specproof --help` lists all 14 commands.
- requirements.lock exists.

STOP CONDITIONS
Three failed attempts on the same error: write review/BLOCKED.md (error, attempts,
hypothesis) and stop.

OUTPUT
The SESSION SUMMARY block from .bob/rules/03-session-evidence.md.
```

## V: Ask mode
```text
Run `make check` and `specproof --help`. Paste both outputs verbatim, with no commentary.
```

## Human acceptance
- [ ] `make check` green on your machine · [ ] `git status` shows no stray files · [ ] commit `T01: scaffold` · [ ] export + screenshot + INDEX row
