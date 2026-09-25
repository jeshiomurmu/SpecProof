# Test Plan: SpecProof

Version 1.0 · 2026-09-25

> **Why test code is not pre-written in this kit:** the hackathon evaluates how IBM Bob 2.0 built the project, and the submission must show files Bob assisted with. Test IDs, fixtures and assertions below are **binding specifications**. Bob implements each test **first** within its task card (AGENTS.md §6), and the session exports then show test-driven development done in Bob.

## 1. Strategy

| Level | Scope | Data | Marker | Runs in |
|---|---|---|---|---|
| Unit | Pure functions (text, models, rules) | Synthetic strings and fixtures | `unit` | `make check` |
| Integration | Engine, loop, compare, conformance, report | Synthetic PDF + golden contracts + mini client | `integration` | `make check` |
| E2E synthetic | Whole pipeline on the synthetic PDF | FX-01..FX-05 | `e2e` | `make test-e2e` |
| E2E real | The real UniFi PDF and client | Pinned sources (`make fetch`) | `real_source` | `make test-e2e`; skipped if sources are absent |
| Governance | Repo hygiene rules | The git tree | `unit` | `make check` |

**Tooling:** pytest, pytest-cov (`--cov=specproof --cov-fail-under=85`, excluding `cli.py`), hypothesis (property tests), reportlab (fixture PDF builder), openapi-spec-validator.

**Naming:** `test_<ID>_<short_description>`, for example `test_VER_004_fabricated_quote_fails`. Parametrized tests keep the ID and use readable `ids=`.

## 2. Fixtures

| ID | Fixture | Contents | Purpose |
|---|---|---|---|
| FX-01 | `tests/fixtures/build_synthetic_pdf.py` + `synthetic_spec.yaml` | A 7-page PDF drawn with reportlab. Table columns sit at **fixed x-positions**, so layout extraction yields multi-space separators. Contents:<br>• p1: TOC with dotted leaders<br>• p2: `1.1 Overview`<br>• p3: `2.1 Schemas` defining `color: enum shade {Red,Green,Blue}`<br>• p4–5: `2.2 Create Widget`, `POST /api/v1/widgets`. Header row `Authorization  T  String`; body rows `name T String`, `color T String`, `size F Integer`, and `notes F String` with a description wrapped over 2 lines. Response Sample JSON. Request Sample curl `--data-raw` containing `"color": "Grean"` (planted enum defect). The section spans a page break.<br>• p6: `2.3 Fetch Widget`, `GET /api/v1/widgets/:id`, response sample<br>• p7: `2.4 Broken Sample`, a request sample with a trailing comma (malformed) | Offline stand-in for the real PDF, with known answers |
| FX-02 | `tests/fixtures/contracts_good/*.json` | Hand-written correct contracts for S-2.1..S-2.4 of FX-01 | Golden inputs |
| FX-03 | `conftest.mutate(contract, kind)` | Mutations: `fabricate_quote`, `wrong_page`, `flip_required`, `flip_type`, `drop_field`, `enum_not_grounded`, `repair_sample`, `wrong_path`, `wrong_method`, `short_quote`, `name_not_in_quote` | Each must trigger exactly its reason code |
| FX-04 | `tests/fixtures/mini_client/` | `client.py`:<br>• `self._request("GET", f"/api/v1/widgets/{widget_id}")`<br>• `self.session.post("/api/v1/widgets", …)`<br>• an undocumented `"/api/v1/gadgets"`<br>• a dynamic path built by `"/".join(parts)`<br>`models.py`: Pydantic `Widget` with `size: int` (required, but the doc marks it optional and the doc response sample omits it), `created_at: str` (doc: Integer), and a `serial: str` field that is absent from the doc | Conformance known answers |
| FX-05 | `tests/fixtures/community_min.yaml` | OpenAPI 3.1 with deliberate diffs vs FX-02: `size` marked required, `name` typed integer, `color` enum missing `Blue`, missing `DELETE` endpoint, and paths **without** leading slash plus `{widget_id}` vs `:id` naming (must NOT be a diff) | Compare known answers |
| FX-06 | `tests/fixtures/state_metrics.json` | A hand-built pipeline state with known counts | Metric formulas |
| FX-07 | `tmp_git_repo` fixture | Temporary git repo with a base commit | Guard and governance tests |

## 3. Test catalog

### 3.1 `util/text` (TXT)

| ID | Test | Assertion |
|---|---|---|
| TXT-001 | NFKC normalization | `norm("ｆｉｒｓｔ")=="first"` |
| TXT-002 | Whitespace collapse | `norm("a \n\t  b")=="a b"` |
| TXT-003 | Smart quotes | `norm("“x”")=='"x"'` |
| TXT-004 | Idempotence (hypothesis) | `norm(norm(s))==norm(s)` for arbitrary text |
| TXT-005 | Row tokens | `row_tokens("  first_name   T   String   First")==("first_name","T","String")` |
| TXT-006 | Prose rejected | `row_tokens("the first_name T is String")` is None (needs ≥ 2 spaces between columns) |

### 3.2 Models (MOD)

| ID | Test | Assertion |
|---|---|---|
| MOD-001 | Quote min length | Citation with an 11-char normalized quote raises ValidationError |
| MOD-002 | Quote max length | 201 chars raises |
| MOD-003 | Page ≥ 1 | page=0 raises |
| MOD-004 | Type vocabulary | `type="str"` raises; the 7 allowed values pass |
| MOD-005 | Kind constraints | endpoint without method/path raises; schema with method raises |
| MOD-006 | Schema version | `schema_version=2` rejected with a clear message |
| MOD-007 | Deterministic dump | Dumping the same object twice gives identical bytes; keys sorted; trailing newline |
| MOD-008 | Stable finding ID | Same finding with evidence in a different order gives the same `id` |

### 3.3 Fetch (FET)

| ID | Test | Assertion |
|---|---|---|
| FET-001 | Hash mismatch | Local `file://` source with a wrong sha → exit 1, file not kept |
| FET-002 | Cache hit | Existing file with the correct hash is not re-downloaded (downloader called 0 times) |
| FET-003 | Git pin | Local bare-repo fixture is checked out at the pinned commit (HEAD == pin) |

### 3.4 Ingest (ING)

| ID | Test | Assertion |
|---|---|---|
| ING-001 | Page count | FX-01 gives 7 pages |
| ING-002 | Layout fidelity | Page 4 text has a line matching the row regex for `color T String` |
| ING-003 | Stable hashes | Page sha256 values are identical across two runs |
| ING-004 | Manifest | Records extractor name + version + input sha |
| ING-005 | Extractor selection | `auto` picks pdftotext when `shutil.which` finds it, else pdfplumber (monkeypatch) |
| ING-006 | Extractor parity | On FX-01, both extractors produce the same set of detected row names |
| ING-R01 | *real_source* | Page 14 contains the `first_name T String` row |
| ING-R02 | *real_source* | 194 pages; input sha == pin |

### 3.5 Segment (SEG)

| ID | Test | Assertion |
|---|---|---|
| SEG-001 | TOC skipped | No section is created from dotted-leader lines on p1 |
| SEG-002 | Heading detection | Sections S-1.1, S-2.1, S-2.2, S-2.3, S-2.4 found |
| SEG-003 | Endpoint kind | S-2.2 `kind=="endpoint"` (contains `Request URL:`) |
| SEG-004 | Schema kind | S-2.1 `kind=="schema"` |
| SEG-005 | Page span | S-2.2 `page_start==4`, `page_end==5` |
| SEG-006 | Hints | S-2.2 `method_hint=="POST"`, `path_hint=="/api/v1/widgets"` |
| SEG-007 | Order and IDs | Sorted by numeric section number; IDs stable |
| SEG-008 | No full text | `sections_index.json` values contain no field longer than 200 characters |
| SEG-R01 | *real_source* | ≥ 107 endpoint sections |
| SEG-R02 | *real_source* | S-4.1 is `schema`, and 52 ∈ its page range |
| SEG-R03 | *real_source* | S-3.2 hints: POST `/api/v1/developer/users` |

### 3.6 Grounding (VER)

| ID | Test | Assertion |
|---|---|---|
| VER-001 | Exact quote | Passes |
| VER-002 | Whitespace-variant quote | Passes |
| VER-003 | Short quote | `V2_QUOTE_TOO_SHORT` |
| VER-004 | Fabricated quote | `V2_CITATION_NOT_FOUND`; issue carries a `closest_match` hint |
| VER-005 | Wrong page | `V2_CITATION_WRONG_PAGE` with `suggested_page` = the true page |
| VER-006 | Name not in quote | `V2_NAME_NOT_IN_QUOTE` |
| VER-007 | Required flipped | `V2_ROW_MISMATCH` (T vs false) |
| VER-008 | Type flipped | `V2_ROW_MISMATCH` (String vs integer) |
| VER-009 | Wrapped row | `notes` gets `V2_ROW_NOT_FOUND` with severity info; no error |
| VER-010 | Enum not grounded | `V2_ENUM_NOT_GROUNDED` when `Purple` is added to the enum |
| VER-011 | Enum via schema page | `color` enum grounded via `enum_citation` on p3 passes |
| VER-012 | Fuzzy never decides | Monkeypatching rapidfuzz to return 100 or 0 leaves pass/fail unchanged |
| VER-013 | Repaired sample | `repair_sample` mutation ("Grean" → "Green" in `raw` only) gives `V2_SAMPLE_NOT_VERBATIM` |

### 3.7 Samples (SMP)

| ID | Test | Assertion |
|---|---|---|
| SMP-001 | curl parsing | JSON extracted from `--data-raw '…'` across line breaks |
| SMP-002 | Malformed | Trailing comma gives `V3_SAMPLE_UNPARSEABLE` |
| SMP-003 | Required missing | Drop `name` from the sample → `V3_REQUIRED_MISSING` (warning) |
| SMP-004 | Type mismatch | `"size": "3"` → `V3_TYPE_MISMATCH` |
| SMP-005 | Enum violation | `"Grean"` → `V3_ENUM_VIOLATION` |
| SMP-006 | Unknown key | `"extra": 1` → `V3_UNKNOWN_FIELD` (info) |
| SMP-007 | Placeholders | `{{host}}`, `wHFmHR******kD6wHg` and `example@*.com` produce no issues |
| SMP-008 | Response envelope | Response sample validated for `code`, `msg`, `data` and documented response fields |
| SMP-009 | Schema build golden | JSON Schema built from FX-02 S-2.2 equals `tests/fixtures/golden/schema_S-2.2.json` |

### 3.8 Structure (STR)

| ID | Test | Assertion |
|---|---|---|
| STR-001 | Invalid JSON contract | `V1_SCHEMA_INVALID`; no exception escapes |
| STR-002 | Method mismatch | `V4_METHOD_MISMATCH` |
| STR-003 | Path mismatch | `V4_PATH_MISMATCH` |
| STR-004 | Path normalization | `api/v1/widgets/:id` ≡ `/api/v1/widgets/{widget_id}` gives no issue |
| STR-005 | Coverage gap | Dropping `size` gives `V5_COVERAGE_GAP` |
| STR-006 | Extra grounded field | A grounded field not detected as a row is not flagged |

### 3.9 Engine (ENG), integration

| ID | Test | Assertion |
|---|---|---|
| ENG-001 | Good contracts | FX-02 S-2.1..S-2.3 produce zero extraction-category issues |
| ENG-002 | Order | Issues sorted by (rule order, field, code) |
| ENG-003 | Determinism | Identical result bytes across 2 runs |
| ENG-004 | Mutation matrix | Parametrized over FX-03: each mutation produces **exactly** its expected code, and no other extraction-category code |
| ENG-005 | Counts | `items`, `grounded`, `row_checked`, `row_ok` equal hand-computed values |

### 3.10 Loop and classification (LOOP)

| ID | Test | Assertion |
|---|---|---|
| LOOP-001 | Clean | S-2.3 → `VERIFIED` |
| LOOP-002 | Grounded conflict | S-2.2 (Grean) → `VERIFIED_WITH_SPEC_FINDINGS`, plus one `SPEC_SELF_INCONSISTENCY` with 2 doc evidences (p3 enum, p5 sample) |
| LOOP-003 | Retry | Mutated S-2.2 at attempt 1 → `NEEDS_RETRY`, and `feedback/S-2.2.md` exists |
| LOOP-004 | Quarantine | Same at attempt 3 → `QUARANTINED` |
| LOOP-005 | Ungrounded conflict | Enum violation while the field citation is fabricated → `NEEDS_RETRY`, **no** finding (ADR-006) |
| LOOP-006 | Feedback content | Lists only failing items, each with code, message, evidence and closest-match; passing items not mentioned |
| LOOP-007 | Feedback determinism | Identical bytes across runs |
| LOOP-008 | Malformed sample finding | S-2.4 with grounded sample citation → `SPEC_MALFORMED_SAMPLE` |
| LOOP-009 | loop-status | `--json` lists exactly the NEEDS_RETRY sections with attempt < 3 |
| LOOP-010 | Downstream exclusion | QUARANTINED sections are absent from export, compare and conform inputs |

### 3.11 Guard (GRD)

| ID | Test | Assertion |
|---|---|---|
| GRD-001 | Protected change | A modified file under `tests/` relative to the base commit makes guard exit 1 and name the path |
| GRD-002 | Allowed change | Changes only under `artifacts/contract/` → exit 0 |

### 3.12 Compare (CMP)

| ID | Test | Assertion |
|---|---|---|
| CMP-001 | Export valid | Exported OpenAPI passes openapi-spec-validator |
| CMP-002 | Verified only | Only VERIFIED and VERIFIED_WITH_SPEC_FINDINGS sections are exported |
| CMP-003 | Normalization regression | FX-05's slash-less and param-renamed paths produce **no** endpoint diffs |
| CMP-004 | Required mismatch | `COMMUNITY_REQUIRED_MISMATCH` on `size`, with our PDF citation |
| CMP-005 | Type mismatch | `COMMUNITY_TYPE_MISMATCH` on `name` |
| CMP-006 | Enum mismatch | `COMMUNITY_ENUM_MISMATCH` on `color` (missing Blue) |
| CMP-007 | Missing endpoint | `COMMUNITY_MISSING_ENDPOINT` for DELETE |
| CMP-008 | Determinism | Sorted, identical bytes across runs |

### 3.13 Conformance (CNF)

| ID | Test | Assertion |
|---|---|---|
| CNF-001 | Constant path | `/api/v1/widgets` found with method POST |
| CNF-002 | f-string path | Normalized to `/api/v1/widgets/{}` |
| CNF-003 | Method via attr | `session.post` → POST |
| CNF-004 | Method via helper | `_request("GET", …)` → GET |
| CNF-005 | Undocumented | `/api/v1/gadgets` → `CLIENT_UNDOCUMENTED_ENDPOINT` with file:line |
| CNF-006 | Dynamic | `"/".join(parts)` → UNCHECKABLE, not a finding |
| CNF-007 | Mapping citation check | A mapping whose file:line lacks `class Widget` is rejected with a clear error |
| CNF-008 | Introspection | Reads alias, required and annotation from `model_fields` |
| CNF-009 | Undocumented required | `serial` → `CLIENT_REQUIRES_UNDOCUMENTED_FIELD` |
| CNF-010 | Type mismatch | `created_at: str` vs doc Integer → `CLIENT_TYPE_MISMATCH` |
| CNF-011 | Replay generation | One test per mapping; file compiles (`py_compile`); deterministic |
| CNF-012 | Replay finding | Doc sample lacks `size` → `CLIENT_SAMPLE_REJECTED`, with the Pydantic error, doc citation and code citation |
| CNF-013 | Env failure | Import error in the client is reported as `environment_error`, not a finding |
| CNF-R01 | *real_source* | Inventory of py-unifi-access finds 11 distinct `/api/v1/developer/` paths (F10) |

### 3.14 Metrics and eval (MET, EVL)

| ID | Test | Assertion |
|---|---|---|
| MET-001 | Formulas | Parametrized over EVALUATION_FRAMEWORK §2 keys: values from FX-06 equal hand-computed ones |
| MET-002 | Denominators | Every rate in `metrics.json` has `numerator` and `denominator` |
| MET-003 | Truncation | 0.89999 displayed as 89.9%, never 90.0% |
| MET-004 | Wilson CI | 38/40 → [0.8350, 0.9862]; 40/40 → [0.9124, 1.0]; 36/40 → [0.7695, 0.9604] (±1e-4) |
| EVL-001 | Pass | All metrics meet thresholds → exit 0 |
| EVL-002 | Fail | One metric below `min` → exit 1, and the metric is named |
| EVL-003 | Max | `quarantine_rate` above `max` → exit 1 |
| EVL-004 | Missing metric | Fails with a message; never passes silently |
| EVL-005 | Result file | `eval_result.json` lists each metric, threshold and verdict |

### 3.15 Report (RPT)

| ID | Test | Assertion |
|---|---|---|
| RPT-001 | Renders | HTML is produced from the synthetic state |
| RPT-002 | Self-contained | No `src=` or `href=` pointing to `http(s)://` (except plain anchor links in the prior-art section, which are allowed) |
| RPT-003 | Finding coverage | Every finding ID appears in the HTML |
| RPT-004 | Evidence | Every doc evidence shows the page number and quote; every code evidence shows file:line |
| RPT-005 | SARIF | `version=="2.1.0"`; each code finding has `locations[0].physicalLocation` |
| RPT-006 | Denominators shown | Hero metrics render as "a/b (x%)" |
| RPT-007 | Deterministic body | No timestamps in the HTML body (the generated-at time lives only in the footer attribute read from the manifest) |

### 3.16 CLI (CLI)

| ID | Test | Assertion |
|---|---|---|
| CLI-001 | Help | `--help` lists every command in the architecture doc §10 |
| CLI-002 | Missing source | `ingest` without `spec.pdf` → exit 2 |
| CLI-003 | Verify exit | NEEDS_RETRY present → exit 1 |

### 3.17 Governance (GOV)

| ID | Test | Assertion |
|---|---|---|
| GOV-001 | No sources tracked | `git ls-files` contains no `*.pdf`, `pages.jsonl` or `community_openapi.yaml` |
| GOV-002 | Quote length | Every committed contract quote is ≤ 200 characters |
| GOV-003 | No network in core | AST scan: `requests`, `httpx`, `urllib.request`, `aiohttp` and `socket` are imported only in `sources/fetch.py` |
| GOV-004 | Manifest completeness | Every committed artifact has a manifest entry with a matching sha256 |
| GOV-005 | Secrets tooling | `.pre-commit-config.yaml` contains a gitleaks hook |

### 3.18 End-to-end (E2E)

| ID | Test | Assertion |
|---|---|---|
| E2E-001 | Synthetic pipeline | FX-01 + FX-02 → statuses {S-2.2: VERIFIED_WITH_SPEC_FINDINGS, S-2.3: VERIFIED, S-2.4: VERIFIED_WITH_SPEC_FINDINGS}; the report contains the Grean finding |
| E2E-002 | Determinism | Two full runs into temporary dirs give identical sha256 for every committed-type artifact |
| E2E-003 | Performance | Synthetic pipeline < 10 s |
| E2E-R01 | *real_source*: F7 reproduced | `SPEC_SELF_INCONSISTENCY` for `visit_reason` in S-4.2 (evidence pages include 52 and 56) and in S-4.5 (52 and 63). Runs after T08 |
| E2E-R02 | *real_source* | `endpoint_coverage` ≥ 0.90 |
| E2E-R03 | *real_source* | Determinism on real artifacts |

## 4. Test-to-task map

| Task | Tests written in that task |
|---|---|
| T01 | CLI-001, GOV-005 |
| T02 | TXT-*, FET-*, ING-*, GOV-001, GOV-003 |
| T03 | SEG-* |
| T04 | MOD-* |
| T05 | VER-* (incl. VER-013), SMP-*, STR-*, ENG-* |
| T06 | LOOP-*, GRD-*, CLI-003 |
| T09 | CMP-* |
| T10 | CNF-* |
| T11 | MET-*, EVL-* |
| T12 | RPT-*, GOV-002, GOV-004, E2E-001..003, CLI-002 |
| After T08 | E2E-R01..R03 (already written in T12; they turn green once real contracts exist) |

## 5. Commands
```bash
make check        # ruff + mypy --strict + pytest -m "unit or integration" with coverage gate
make test-e2e     # pytest -m "e2e or real_source"
pytest -k VER_004 # run a single test by ID
```
