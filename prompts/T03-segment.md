# T03: Deterministic segmenter

Est. 60 min · Modes: Plan → Agent · Tests: SEG-001..008, SEG-R01..R03
Pre-flight: `git rev-parse HEAD > .specproof_task_base && make check`

## P: Plan mode
```text
Task T03. Read AGENTS.md, docs/TECHNICAL_ARCHITECTURE.md sections 3, 5.4 and ADR-002,
docs/TEST_PLAN.md SEG rows, docs/VERIFIED_FACTS.md F3, F4, F5 and F9.
Plan in at most 15 lines: the heading-detection algorithm, false-positive defenses, kind rules,
page-range logic, hint parsing. No edits.
```

## A: Agent mode
```text
ROLE
Lead engineer on SpecProof. AGENTS.md is binding. Test-first.

TASK
T03: implement src/specproof/ingest/segment.py and `specproof segment`, producing
artifacts/sections_index.json from artifacts/work/pages.jsonl. Fully deterministic; no LLM.

ALGORITHM (implement exactly; deviations need a written reason in review/SEG_NOTES.md)
1. TOC pages: a page is a TOC page if at least 5 of its lines match r"\.{5,}\s*\d+\s*$".
   Ignore all headings on TOC pages.
2. Heading candidates: lines matching r"^\s{0,12}(\d{1,2})\.(\d{1,2})\s+([A-Z][^\n]{1,80}?)\s*$",
   excluding lines that also match the dotted-leader pattern.
   Version strings such as "1.22.16 or later" must NOT match (the second number is followed by
   ".", not whitespace).
3. Monotonic filter: walk candidates in document order. Accept a candidate only if
   (chapter, number) is strictly greater than the last accepted one and chapter >= the last
   chapter. This rejects stray matches inside tables and samples.
4. Section text = from the heading line up to (not including) the next accepted heading.
   page_start = the page of the heading; page_end = the page of the last line before the next
   heading.
5. kind: "endpoint" if the section text contains "Request URL:"; "schema" if the title contains
   "Schema"; otherwise "overview".
6. Hints: method_hint from r"Method:\s*([A-Z]+)", path_hint from r"Request URL:\s*(\S+)".
   Normalize path_hint: drop any query string; ensure a leading "/"; strip a trailing "/".
   Keep ":id"-style parameters as printed. Normalization for comparison is done elsewhere.
7. section_id = f"S-{chapter}.{number}"; text_sha256 = sha256 of norm(section text).
8. Output list sorted by (chapter, number). Write it with util/io_json.dump_json and append a
   manifest record (stage "segment").
   The index must contain NO section text: only id, chapter, number, title, kind,
   page_start, page_end, method_hint, path_hint, text_sha256.
   Also write artifacts/work/sections.jsonl (id + full text) for later stages; it is gitignored.

TESTS FIRST
tests/unit/test_segment.py: SEG-001..008 against the synthetic_pdf fixture (FX-01) after
ingest. tests/e2e/test_real_source.py: SEG-R01 (>= 107 endpoint sections), SEG-R02 (S-4.1 is
schema, 52 in [page_start, page_end]), SEG-R03 (S-3.2 hints POST /api/v1/developer/users).

THEN
Run on the real PDF: `specproof ingest && specproof segment`. Print counts by kind and
the first 5 and last 5 entries of the index.
- If the endpoint count is not 107, do NOT tune the algorithm to force the number. Investigate:
  list the (method, path) pairs from "Request URL:" lines that are not inside an accepted
  endpoint section. Write findings to review/SEG_NOTES.md, fix only genuine bugs, and report
  the true number.

CONSTRAINTS
Pure functions for segmentation logic; I/O only in cli.py. mypy --strict. No LLM.

ACCEPTANCE CRITERIA
make check green; make test-e2e shows SEG-R01..R03 passed; artifacts/sections_index.json
committed; counts by kind reported verbatim.

STOP CONDITIONS
Three failed attempts on the same error: review/BLOCKED.md, then stop.

OUTPUT
SESSION SUMMARY.
```

## V: Ask mode
```text
Run: specproof segment && python -c "import json,collections;d=json.load(open('artifacts/sections_index.json'));print(collections.Counter(x['kind'] for x in d));print([x for x in d if x['section_id'] in ('S-3.2','S-4.1','S-4.2','S-4.5')])"
Paste the output verbatim.
```
