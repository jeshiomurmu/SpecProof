# AGENTS.md: System instructions for SpecProof

You are the engineering partner on **SpecProof**, a tool that turns document-only API specifications into verified, cited contracts and checks real code against them. This file applies to **every** mode and every task. Read it fully at the start of each task.

## 1. Mission (one sentence)
AI proposes; deterministic code decides. Every claim SpecProof makes must trace to a page and a verbatim quote in the source document, or to a file and line in code.

## 2. Non-negotiable rules
1. **Never fabricate.** Never invent numbers, citations, page numbers, quotes, test results or metrics. If you did not run it, do not report it. If a value is unknown, write `UNKNOWN`.
2. **No model judges its own output.** Verification logic in `src/specproof/verify/` is pure deterministic Python. It must never call an LLM.
3. **Never commit third-party source documents.** The spec PDF and full-page text stay in `artifacts/work/`, which is gitignored. Committed artifacts may contain only short quotes (≤ 200 characters each).
4. **Tests are the contract.** Never delete, skip, or weaken a test to make it pass. Never edit `eval/thresholds.yaml` to make a gate pass. If a test is wrong, stop and write the reason in `review/BLOCKED.md`.
5. **Network access only in `specproof fetch`.** Unit and integration tests run fully offline.
6. **No secrets anywhere.** Do not create API tokens, and do not call the real UniFi API. SpecProof is offline analysis only.
7. **Stay in scope.** Implement only the current task card from `docs/IMPLEMENTATION_PLAN.md`. Note ideas in `review/IDEAS.md` instead of building them.
8. **Stop after 3 failed attempts** on the same error. Write `review/BLOCKED.md` with the error, what you tried, and your hypothesis. Then stop.

## 3. Repository map
```
src/specproof/        product code (models, ingest, verify, loop, compare, conformance, report)
tests/                pytest suites: unit/ integration/ e2e/ (markers: unit, integration, e2e, real_source)
tests/fixtures/       synthetic PDF builder + mini client; NEVER the real vendor PDF
artifacts/contract/   extracted contracts, one JSON per section (committed)
artifacts/work/       fetched sources, page text, sections (gitignored)
artifacts/            verification/, feedback/, findings/, report/, metrics.json (committed)
docs/                 PRD, architecture, governance, quality, plan, evaluation, tests, loops
eval/                 thresholds.yaml, audit/ (hand-audit CSV + protocol)
sources/              sources.lock.yaml (URLs + SHA-256 pins)
.bob/                 custom mode, rules, skills, commands
bob_sessions/         exported Bob task sessions + screenshots + INDEX.md
```

## 4. Commands (always use these)
| Command | Purpose |
|---|---|
| `make setup` | Create venv, install deps, install pre-commit hooks |
| `make check` | ruff + mypy + pytest (unit + integration). **Must be green before any commit.** |
| `make test-e2e` | End-to-end tests, including `real_source` (needs `make fetch`) |
| `make fetch` | Download pinned sources and verify SHA-256 |
| `make pipeline` | ingest → segment → verify → classify → compare → conform → report |
| `make eval` | Compute metrics and compare against `eval/thresholds.yaml` |
| `make guard` | Fail if protected paths changed (see §8) |

## 5. Engineering standards
- Python 3.11+, full type hints, and `mypy --strict` on `src/`.
- Pydantic v2 for every data model. JSON output uses sorted keys, 2-space indent, UTF-8, and a trailing newline.
- **Determinism:** the same inputs must always give byte-identical outputs. Sort every collection before writing. No timestamps inside content hashes; timestamps go only in `manifest.json`.
- Pure functions in the core. I/O happens only in `cli.py` and `io_*` helpers. Use `pathlib` everywhere.
- Log with `logging`; no `print` in library code.
- The CLI uses Typer. Exit codes: 0 = success, 1 = verification or gate failure, 2 = usage or config error.
- Keep modules under 300 lines and functions under 50 lines where practical.
- Every public function gets a one-line docstring saying what it guarantees.

## 6. Testing protocol (test-first)
1. Before implementing a task, write its tests from `docs/TEST_PLAN.md`. Use the exact test IDs in function names, e.g. `test_VER_004_fabricated_quote_fails`.
2. Run the tests and confirm they fail for the right reason.
3. Implement until `make check` is green.
4. Keep line coverage of `src/specproof` (excluding `cli.py`) at 85% or higher.
5. Unit tests use synthetic fixtures only. Tests on the real PDF are marked `@pytest.mark.real_source` and are skipped when the sources are absent.

## 7. Task protocol (one task card = one Bob task)
1. Read the task card in `docs/IMPLEMENTATION_PLAN.md`, plus any documents it references.
2. **Plan mode first:** restate the goal, list the files you will touch, and name the tests you will write. Keep it to 15 lines or fewer.
3. Switch to Agent mode and implement test-first.
4. Run `make check`. It must be green.
5. Update `docs/CHANGELOG.md` with one line: `T0X: <what changed>`.
6. Commit with a Conventional Commits message (`feat: …`, `fix: …`, `test: …`, `docs: …`, `chore: …`), imperative and specific, with the task ID as a body trailer: `Refs: T0X`.
7. Remind the human to export this session to `bob_sessions/exports/` and screenshot the consumption summary.

## 8. Protected paths (reward-hacking guard)
Extraction tasks (using `spec-auditor` mode) must **not** modify:
- `src/specproof/verify/**`
- `tests/**`
- `eval/thresholds.yaml`
- `sources/sources.lock.yaml`

`make guard` enforces this whenever the marker file `.specproof_extraction_task` exists. The human creates it before extraction tasks (`touch .specproof_extraction_task`) and deletes it afterwards. Changing verification logic and extraction output in the same task is forbidden.

## 9. Bobcoin economy
- Use Ask mode for questions. Use Plan mode to scope work. Use Agent mode only for edits.
- Reference files by path. Never paste or re-read the whole PDF; the skill tells you which pages to read.
- One chapter per subagent. Subagents return only JSON contract files and a 3-line summary.
- Cache everything. Never re-extract a section whose `artifacts/verification/<id>.json` status is `VERIFIED`.

## 10. Definition of done (every task)
- `make check` is green, and coverage has not dropped.
- The listed test IDs exist and pass.
- `make guard` passes.
- There is a CHANGELOG line and a commit.
- No new TODOs without an entry in `review/IDEAS.md`.
