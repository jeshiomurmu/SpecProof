# Implementation Plan / Task Breakdown: SpecProof

Version 1.0 · All times are **Bangladesh Standard Time (BST, UTC+6)** · Kickoff Fri 25 Sep 21:00 · **Internal submit target Sun 27 Sep 18:00** · Hard deadline 21:00

## 1. Timeline

| Block | When | Tasks | Exit criterion |
|---|---|---|---|
| Pre-event | Fri until 21:00 | T00 | Kit committed; tools installed |
| Kickoff | Fri 21:00–22:30 | Watch stream; Discord Q&A; update `VERIFIED_FACTS.md` U1–U5 | Bob access working; Bobcoin budget known |
| Night 1 | Fri 22:30–02:00 | T01, T02, T03 | Real PDF segmented; `SEG-R01` green |
| Sleep | 02:00–07:30 | — | — |
| Day 2 AM | Sat 07:30–12:30 | T04, T05, T06 | Verifier + loop green on synthetic |
| Day 2 PM | Sat 12:30–18:30 | T07 (pilot), T08 (extraction + loop) | All sections terminal; E2E-R01 green |
| Day 2 eve | Sat 18:30–23:30 | T09, T10, T11 | Compare + conformance + eval running |
| Sleep | 23:30–05:30 | — | — |
| Day 3 AM | Sun 05:30–10:30 | T12, T13 | Report + audit + confirmed findings |
| Day 3 midday | Sun 10:30–14:30 | T14, T15a | Site live; README results; video recorded |
| Day 3 PM | Sun 14:30–18:00 | T15b | **Submitted by 18:00** |
| Buffer | Sun 18:00–21:00 | — | Fixes only; nothing new |

**Critical path:** T01 → T02 → T03 → T04 → T05 → T06 → T07 → T08 → T12 → T14 → T15. Tasks T09, T10 and T11 can slip, and the cut list (§4) says what goes first.

## 2. Bobcoin budget
Update this table at kickoff (U1). The shares below assume a tight allowance like May's 40 coins.

| Tier | Tasks | Share | Tactics |
|---|---|---|---|
| Engine build | T01–T06, T09–T12 | 45% | Plan mode for scoping; Agent mode in one pass with tests; reference files by path |
| Extraction | T07–T08 (incl. loop) | 40% | Pilot 2 sections first; chapter subagents; never re-extract VERIFIED; early stop when not converging |
| Reserve | Fixes, polish | 15% | Hold back until Sunday |

**If the budget is lower than expected:** extract chapters in order of value — 4 (Visitor: contains F7), 3 (User), 5, … — and stop at the gate threshold (`endpoint_coverage` min 0.90). If coins run out below that, report the actual coverage honestly and scope claims to the chapters extracted.

## 3. Task cards

Each card lists: goal · mode · inputs → outputs · tests · acceptance · estimate · a short Bob prompt.

> **Use the production prompts in `prompts/` instead of the short prompts below.** `prompts/T0X-*.md` contains the full Plan / Agent / Ask blocks, subagent briefs, acceptance criteria and stop conditions. The short prompts here are summaries only. Recovery prompts: `prompts/R-recovery.md`. Claude Code prompts: `prompts/CC-claude-code.md`.

---

### T00: Bootstrap (human, pre-event, 30 min)
- Create the public GitHub repo `specproof` (MIT). Copy this kit in. Add `.gitignore` covering `artifacts/work/`, `.venv/`, caches and `.specproof_task_base`.
- Commit: `T00: planning kit (pre-event, docs + Bob config only, no product code)`.
- Install: Python 3.11+, git, IBM Bob IDE, poppler (optional, for pdftotext), gitleaks, and Claude Code (optional).

---

### T01: Scaffold (Agent · 45 min)
- **Outputs:** `pyproject.toml` (deps from architecture §12, console script `specproof`), `Makefile` (targets in AGENTS.md §4), `src/specproof/__init__.py`, `cli.py` with every §10 command stubbed (exit 0, "not implemented"), ruff/mypy/pytest config, `.pre-commit-config.yaml` (ruff, mypy, gitleaks), `.github/workflows/ci.yml`, `LICENSE`, `.gitignore`.
- **Tests:** CLI-001, GOV-005
- **Acceptance:** `make setup && make check` green.
- **Bob prompt:**
  > Read AGENTS.md, docs/TECHNICAL_ARCHITECTURE.md sections 10–12, and docs/IMPLEMENTATION_PLAN.md task T01. In Plan mode, list the files you will create and the tests CLI-001 and GOV-005 from docs/TEST_PLAN.md. Then, in Agent mode, write those tests first, create the scaffold, pin dependency versions, and run `make setup` and `make check` until green. Stubs only; no product logic.

---

### T02: Text utils, fetch, ingest (Agent · 75 min)
- **Outputs:** `util/text.py`, `util/io_json.py`, `util/hashing.py`, `sources/fetch.py`, `ingest/extractors.py`, `models/manifest.py` (minimal), CLI `fetch`, `ingest`. Fixture builder FX-01 (`tests/fixtures/build_synthetic_pdf.py` + `synthetic_spec.yaml`).
- **Spike first (15 min, record in `review/SPIKE_T02.md`):** run both extractors on the real PDF pages 14, 52 and 56. Confirm that the `first_name  T  String` row and the `visit_reason` enum line survive with ≥ 2-space separators. Pick the default extractor based on the evidence.
- **Tests:** TXT-001..006, FET-001..003, ING-001..006, ING-R01..R02, GOV-001, GOV-003
- **Acceptance:** `make fetch` verifies all 3 pins; `specproof ingest` writes `pages.jsonl` + manifest; `make check` green.
- **Bob prompt:**
  > Task T02 (see docs/IMPLEMENTATION_PLAN.md). First, the spike: after `make fetch`, extract pages 14, 52, 56 of artifacts/work/spec.pdf with pdftotext -layout and with pdfplumber (layout=True), and write review/SPIKE_T02.md comparing whether table rows keep ≥ 2-space column gaps. Then write the tests listed for T02 in docs/TEST_PLAN.md first, including the FX-01 synthetic PDF builder (fixed x-positions for table columns), and implement util/text.py, sources/fetch.py and ingest/extractors.py to make them pass. Use the extractor the spike favored as the `auto` default.

---

### T03: Segmenter (Agent · 60 min)
- **Outputs:** `ingest/segment.py`, CLI `segment`, `artifacts/sections_index.json` (real PDF, committed).
- **Tests:** SEG-001..008, SEG-R01..R03
- **Acceptance:** real index has ≥ 107 endpoint sections, S-4.1 is a schema section with page 52 in range, and hints for S-3.2 are correct. If the count ≠ 107, investigate and document the reason in `review/SEG_NOTES.md` before accepting.
- **Bob prompt:**
  > Task T03. Write the SEG tests from docs/TEST_PLAN.md first. Implement ingest/segment.py per architecture section 5.4: skip TOC lines with dotted leaders, detect `N.M Title` headings, classify kind (endpoint if the section contains `Request URL:`, schema if the title contains `Schema`, else overview), compute page ranges, parse method/path hints, and store only hashes (no full text). Run on the real PDF and report the counts by kind verbatim.

---

### T04: Data models (Agent · 45 min)
- **Outputs:** `models/contract.py`, `models/verification.py`, `models/findings.py`, the complete `models/manifest.py`; JSON Schema export of `ContractSection` to `docs/schemas/contract.schema.json` (for the skill to reference).
- **Tests:** MOD-001..008
- **Bob prompt:**
  > Task T04. Write the MOD tests first. Implement the Pydantic v2 models exactly as specified in docs/TECHNICAL_ARCHITECTURE.md section 5 (Citation 12–200 chars after normalization, FieldSpec vocabularies, kind constraints, schema_version=1, stable Finding IDs). Export the ContractSection JSON Schema to docs/schemas/contract.schema.json.

---

### T05: Verification engine V1–V5 (Agent · 120 min) ★ riskiest
- **Outputs:** `verify/grounding.py`, `verify/samples.py`, `verify/structure.py`, `verify/engine.py`, CLI `verify`; FX-02 golden contracts; the FX-03 mutation helper.
- **Tests:** VER-001..012, SMP-001..009, STR-001..006, ENG-001..005
- **Acceptance:** the mutation matrix (ENG-004) is green, with each mutation → exactly its code.
- **Optional:** Claude Code review → `review/REVIEW_T05.md`.
- **Bob prompt:**
  > Task T05 — the core. Read architecture sections 6 and 7 carefully. Write all VER, SMP, STR and ENG tests first, including the FX-02 golden contracts for the synthetic PDF and the FX-03 mutation helper in conftest.py. Then implement the rules in the exact order of the catalog, with the exact reason codes. rapidfuzz may only produce closest-match hints and must never influence pass/fail (VER-012). No LLM calls anywhere in verify/. Use subagents if helpful: one for samples.py + its tests, one for grounding.py + its tests.

---

### T06: Loop, classifier, feedback, guard (Agent · 75 min)
- **Outputs:** `loop/classify.py`, `loop/feedback.py`, CLI `loop-status`, `classify`, `guard`; `artifacts/status.json` writer.
- **Tests:** LOOP-001..010, GRD-001..002, CLI-003
- **Bob prompt:**
  > Task T06. Write the LOOP and GRD tests first. Implement the state machine in architecture section 7, including the grounded-conflict rule (ADR-006), feedback files in the exact format shown in docs/LOOP_ENGINEERING.md, early stopping when extraction issues do not strictly decrease between attempts, and `specproof guard` comparing protected paths (AGENTS.md section 8) against the commit in .specproof_task_base.

---

### T07: Extraction pilot (spec-auditor · 30 min)
- **Goal:** validate the mode, skill and commands, and Bob's PDF reading (U2–U4), on 2 sections before spending on everything.
- **Steps:**
  1. Switch to Spec Auditor mode. If it's missing, create it via the UI (START_HERE Step 2.4).
  2. Extract S-3.2 (User Registration) and S-4.1 (Schemas) + S-4.2 (Create Visitor).
  3. `specproof verify --section S-3.2 --section S-4.1 --section S-4.2` → `specproof classify`.
- **Acceptance:** S-3.2 VERIFIED (possibly after 1 retry). S-4.2 VERIFIED_WITH_SPEC_FINDINGS with the `visit_reason` finding. If it fails, **fix the skill wording** (bump `prompt_version` to `extract-v2`) before T08.
- **Bob prompt:**
  > Using the Spec Auditor mode and the specproof-extract skill, extract sections S-4.1, S-3.2 and S-4.2 from artifacts/work/spec.pdf, following the skill exactly. Then run `specproof verify --section S-4.1 --section S-3.2 --section S-4.2` and `specproof classify`, and report the output verbatim.

---

### T08: Full extraction + loop (spec-auditor · 3–4 h, mostly waiting)
- **Steps:**
  1. Run `/sp-extract <chapter>` for each chapter, starting with 4 and then 3. Run several chapters as parallel/background tasks.
  2. Run `/sp-loop` twice, then `specproof classify`.
  3. `make guard`, then commit with the message `T08: extraction complete`.
- **Acceptance:** all sections are terminal; `endpoint_coverage` ≥ 0.90; E2E-R01 is green.
- **Evidence to capture:** a screenshot of the subagent fan-out, a screenshot of parallel tasks, and the per-chapter exports.

---

### T09: OpenAPI export + community compare (Agent · 60 min)
- **Outputs:** `compare/openapi_export.py`, `compare/community.py`, CLI `export-openapi`, `compare`; FX-05.
- **Tests:** CMP-001..008
- **Bob prompt:**
  > Task T09. Write the CMP tests first (FX-05 fixture included; CMP-003 is a regression test for path normalization: leading slash and param names must not produce diffs). Implement the export of VERIFIED and VERIFIED_WITH_SPEC_FINDINGS sections only to OpenAPI 3.1, validated with openapi-spec-validator, and a field-level diff against artifacts/work/community_openapi.yaml producing COMMUNITY_* findings, each carrying our PDF citation.

---

### T10: Conformance on py-unifi-access (Agent + spec-auditor · 120 min)
- **Spike first (15 min):** read `artifacts/work/py-unifi-access/unifi_access_api/client.py` and record its HTTP call pattern in `review/SPIKE_T10.md`.
- **Outputs:** `conformance/inventory.py`, `models.py`, `replay.py`, CLI `conform`; FX-04 mini client; `artifacts/conformance/mapping.yaml` (written by the Spec Auditor mode); `test_sample_replay.py` (generated).
- **Tests:** CNF-001..013, CNF-R01
- **Bob prompts:**
  > (Agent) Task T10. Do the spike first. Then write the CNF tests with the FX-04 mini client, and implement the AST inventory, Pydantic model introspection, mapping validation (file:line must contain the class) and replay test generation + execution in an isolated venv at the pinned commit.

  > (Spec Auditor) Create artifacts/conformance/mapping.yaml, mapping each py-unifi-access response model to the contract section whose response it parses, with json_path and a code citation (file, line of the class definition). Only map what you can cite. Then run `specproof conform --client artifacts/work/py-unifi-access` and report the output verbatim.

---

### T11: Metrics + eval gate + audit tooling (Agent · 60 min)
- **Outputs:** `report/metrics.py`, `evalgate.py`, CLI `eval`, `audit-sample`, `audit-score`; FX-06.
- **Tests:** MET-001..004, EVL-001..005
- **Bob prompt:**
  > Task T11. Write the MET and EVL tests first (MET-004 has exact Wilson reference values). Implement every metric in docs/EVALUATION_FRAMEWORK.md section 2, with explicit numerator/denominator in metrics.json, truncation instead of rounding, the eval gate against eval/thresholds.yaml (do not modify that file), and audit-sample (stratified, seed argument, refuses to overwrite) and audit-score.

---

### T12: Report (Agent · 90 min)
- **Outputs:** `report/html.py`, `templates/report.html.j2`, `report/sarif.py`, CLI `report`; `demo/index.html` landing page.
- **Tests:** RPT-001..007, GOV-002, GOV-004, E2E-001..003, CLI-002
- **Design:** see architecture §9. Hero numbers must show denominators. Include a "How this was built with IBM Bob 2.0" panel linking `bob_sessions/INDEX.md`.
- **Bob prompt:**
  > Task T12. Write the RPT, GOV-002, GOV-004 and E2E tests first. Build a single self-contained HTML report (inline CSS/JS, no external requests, light/dark) with the sections listed in architecture section 9, plus SARIF 2.1.0 for code findings. Every number comes from metrics.json with its denominator. Then run `make pipeline` and `make eval`, and report the results verbatim.

---

### T13: Human audit + finding confirmation (human · 60 min)
1. `specproof audit-sample --n 40 --seed 20260926` → judge 40 items blind (EVALUATION §4) → `specproof audit-score`.
2. Open every CANDIDATE finding against the PDF (and the code). Mark CONFIRMED or REJECTED in `eval/audit/findings_review.csv`, each with a note.
3. Manual baseline: time 3 endpoints by hand (EVALUATION §5). **Best done Saturday night before T08 results are viewed**; if not possible, disclose that.
4. `make pipeline && make eval` → commit `T13: audit + confirmations`.

---

### T14: Deploy + README results (Agent · 45 min)
- Deploy `demo/` + `artifacts/report/` as a static site (Vercel or GitHub Pages).
- Generate the README results table from `metrics.json` (script `scripts/readme_results.py`; never hand-typed).
- Fresh-clone test: `git clone … && make setup fetch pipeline eval` on a clean directory.

---

### T15: Video, slides, submission (human · 4 h total)
Follow `docs/DEMO_AND_SUBMISSION.md` exactly. T15a covers the recording, T15b the slides, form and `bob_sessions` curation.

## 4. Cut list (cut from the top when behind schedule)
1. Stretch goals (version diff, second document)
2. SARIF export (keep JSON + HTML)
3. Model-field diff C2 (keep inventory C1 + sample replay C3)
4. Community compare beyond required/type/enum mismatches
5. Second auditor
6. Chapters beyond the 0.90 coverage gate

**Never cut:** verification rules, loop, report, eval gate, `bob_sessions`, honest metrics.

## 5. Daily stand-up questions (ask yourself at 07:30 Sat and 05:30 Sun)
1. Is the critical path on time? If not, which cut-list item goes now?
2. Bobcoins left vs the tier budget?
3. Any claim in the draft pitch that `metrics.json` doesn't support yet?
