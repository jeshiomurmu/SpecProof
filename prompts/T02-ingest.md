# T02: Text utilities, source fetching, PDF ingest (+ extractor spike)

Est. 75 min · Modes: Plan → Agent (spike) → Agent (build) · Tests: TXT-001..006, FET-001..003, ING-001..006, ING-R01..R02, GOV-001, GOV-003
Pre-flight: `git rev-parse HEAD > .specproof_task_base && make check`

## P: Plan mode
```text
Task T02. Read AGENTS.md, docs/TECHNICAL_ARCHITECTURE.md sections 3, 4, 12 and 13,
docs/TEST_PLAN.md rows TXT, FET, ING, GOV-001, GOV-003 and fixture FX-01,
docs/DATA_GOVERNANCE_AND_LINEAGE.md section 3, and sources/sources.lock.yaml.
Plan in at most 15 lines: modules, public function signatures, fixture builder design,
test files. No edits.
```

## A1: Agent mode (spike: decide the text extractor on evidence)
```text
TASK
T02 spike (15 min max). Decide the default PDF text extractor from evidence, not assumption.

STEPS
1. Implement ONLY src/specproof/sources/fetch.py enough to download the three pinned sources
   in sources/sources.lock.yaml into their `dest` paths:
   - kind=file: stream to <dest>.part, verify sha256, then rename; on mismatch delete the .part
     file and exit 1.
   - kind=git: `git clone` into dest, then `git checkout <commit>`.
   Wire `specproof fetch` to it and run it.
2. In a throwaway script under review/ (not src/), extract pages 14, 52 and 56 of
   artifacts/work/spec.pdf two ways:
   (a) subprocess `pdftotext -layout -f N -l N <pdf> -`
   (b) pdfplumber `page.extract_text(layout=True)`
3. For each extractor, report:
   - whether a line matches ^\s*first_name\s{2,}T\s{2,}String on page 14;
   - whether "enum reason {Interview,Business,Cooperation,Others}" appears on page 52;
   - whether "Interviemw" appears on page 56.
4. Write review/SPIKE_T02.md: the observed results table (verbatim evidence lines), the
   decision for the `auto` default, and the reason.

CONSTRAINTS
Report only what you observed. If pdftotext is not installed, say so and test pdfplumber only.
Do not start the main implementation.
```

## A2: Agent mode (build)
```text
ROLE
Lead engineer on SpecProof. AGENTS.md is binding. Test-first.

TASK
T02: implement text utilities, source fetching (complete), and page ingestion, plus the
synthetic PDF fixture FX-01.

READ FIRST
review/SPIKE_T02.md; docs/TEST_PLAN.md (TXT, FET, ING, GOV-001, GOV-003, FX-01, FX-07).

DELIVERABLES
1. src/specproof/util/text.py
   - norm(s: str) -> str: unicodedata NFKC; replace “ ” ‘ ’ with straight quotes; collapse
     every whitespace run (incl. newlines, tabs, NBSP) to one space; strip. Idempotent.
   - ROW_RE = r"^\s*(?P<name>[A-Za-z_][\w.\[\]]*)\s{2,}(?P<req>T|F)\s{2,}(?P<type>[A-Za-z][\w\[\]]*)"
   - row_tokens(line: str) -> tuple[str, str, str] | None
2. src/specproof/util/hashing.py: sha256_bytes, sha256_file (streamed), sha256_text (UTF-8).
3. src/specproof/util/io_json.py: dump_json(path, obj) with sort_keys=True,
   ensure_ascii=False, indent=2, trailing newline, atomic write (tmp + os.replace);
   load_json(path).
4. src/specproof/sources/fetch.py (complete): as in the spike, plus the cache hit (existing
   file with the correct sha is not re-downloaded), plus a lock-file loader. The download
   function takes an injectable `opener` so tests can fake the network.
5. src/specproof/ingest/extractors.py
   - @dataclass(frozen=True) Page(number: int, text: str, sha256: str)
   - Protocol TextExtractor with name, version() and extract(pdf: Path) -> list[Page]
   - PdftotextExtractor (subprocess, per page) and PdfplumberExtractor (layout=True)
   - select_extractor("auto" | "pdftotext" | "pdfplumber"): "auto" follows the SPIKE decision
     and falls back when shutil.which("pdftotext") is None.
6. src/specproof/models/manifest.py (minimal): ManifestRecord(artifact, sha256, stage,
   producer: dict, inputs: list[dict], created_at) and append_record(manifest_path, record).
   The manifest stays sorted by artifact path.
7. CLI `ingest`: writes artifacts/work/pages.jsonl (one JSON object per page, sorted by
   number) and appends a manifest record (extractor name + version, input sha).
   Exit 2 if spec.pdf is missing.
8. tests/fixtures/synthetic_spec.yaml + tests/fixtures/build_synthetic_pdf.py implementing
   FX-01 EXACTLY as described in docs/TEST_PLAN.md section 2:
   - reportlab canvas with invariant=1 (so bytes are reproducible), Helvetica 9pt;
   - table columns drawn with drawString at FIXED x positions (e.g. 72, 230, 290, 360, 480),
     so layout extraction yields runs of 2+ spaces;
   - page 1 = TOC with dotted leaders; the S-2.2 section spans pages 4-5;
   - the planted "Grean" enum defect; the S-2.4 trailing-comma sample.
   Expose a session-scoped pytest fixture `synthetic_pdf(tmp_path_factory) -> Path`.
9. Tests, in tests/unit/ unless noted: every row TXT-001..006, FET-001..003, ING-001..006,
   GOV-001, GOV-003; tests/e2e/test_real_source.py with ING-R01, ING-R02 (marked real_source).
   GOV-001 uses `git ls-files`. GOV-003 walks src/ with ast and allows network imports only
   in sources/fetch.py. FET-003 builds a local bare repo with FX-07 (no network).

METHOD
1. Write the tests. Run them and confirm they fail for the right reasons.
2. Implement module by module; run `make check` after each.
3. Run `specproof fetch`, `specproof ingest` and `make test-e2e`; ING-R01 and ING-R02 must pass.

CONSTRAINTS
- Network only inside sources/fetch.py. Unit tests are fully offline.
- Never commit artifacts/work/ (it's gitignored; GOV-001 enforces this).
- mypy --strict clean. Do not lower coverage.

ACCEPTANCE CRITERIA
- make check green (paste its final 5 lines); make test-e2e shows ING-R01 and ING-R02 passed.
- artifacts/manifest.json contains the ingest record with the pinned PDF sha
  d204c8b9ad4d329f6c89e71ebb5ccf446bcc30d2668673011bbe99a909a6a534.

STOP CONDITIONS
Three failed attempts on the same error: review/BLOCKED.md, then stop.

OUTPUT
SESSION SUMMARY (per .bob/rules/03-session-evidence.md).
```

## V: Ask mode
```text
Run `make check`, then `make test-e2e`, then `python -c "import json;print([r for r in json.load(open('artifacts/manifest.json')) if r['stage']=='ingest'])"`.
Paste the outputs verbatim.
```
