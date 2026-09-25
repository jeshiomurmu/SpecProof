# T05: Verification engine V1–V5 (the core; highest risk)

Est. 120 min · Modes: Plan → Agent (with 2 subagents) · Tests: VER-001..013, SMP-001..009, STR-001..006, ENG-001..005
Pre-flight: `git rev-parse HEAD > .specproof_task_base && make check`
After the task: optional Claude Code review (`CC-claude-code.md` → CC-1)

## P: Plan mode
```text
Task T05 (the core of SpecProof). Read, in full: AGENTS.md; docs/TECHNICAL_ARCHITECTURE.md
sections 5, 6, 7 and ADRs 001 and 006; docs/TEST_PLAN.md sections 2 (FX-01, FX-02, FX-03) and
3.6-3.9; docs/LOOP_ENGINEERING.md "Why the loop cannot be gamed".
Produce a plan of at most 25 lines:
(a) how each rule is implemented, in catalog order;
(b) how sections.jsonl and pages.jsonl are loaded;
(c) the FX-02 golden contracts you will hand-write;
(d) the FX-03 mutation list;
(e) how you will split work across 2 subagents.
No edits.
```

## A: Agent mode
```text
ROLE
Lead engineer on SpecProof. AGENTS.md is binding. Test-first. This is the component judges
will scrutinize: correctness over speed.

TASK
T05: implement the deterministic verification engine (rules V1-V5), `specproof verify`, and
the test fixtures FX-02 and FX-03. No LLM calls anywhere in src/specproof/verify/.

INPUTS AT RUNTIME
artifacts/contract/<id>.json (from Bob), artifacts/work/pages.jsonl,
artifacts/work/sections.jsonl, artifacts/sections_index.json.

RULES (exact codes; run in this order; catalog = architecture section 6)
V1  Load with ContractSection.load. On ValidationError or JSON error, emit one
    V1_SCHEMA_INVALID (category extraction) and stop checking that section.
V2  For every Citation in the contract (fields, enum_citation, citations{}, samples):
    - V2_QUOTE_TOO_SHORT if len(norm(quote)) < 12. (Normally unreachable because of the
      model validator; keep it as defense in depth.)
    - Grounded if norm(quote) is a substring of norm(page_text[page]).
    - If not grounded on the cited page but grounded on another page within the section's
      [page_start, page_end]: V2_CITATION_WRONG_PAGE, with hint {"suggested_page": n}.
    - Otherwise V2_CITATION_NOT_FOUND, with hint {"closest_match": <best rapidfuzz
      partial_ratio window over the section pages>, "closest_page": n}.
      rapidfuzz ONLY fills hints and never decides grounding (VER-012).
    - V2_NAME_NOT_IN_QUOTE if field.name is not in norm(field.citation.quote).
V2b Row consistency, for fields with location in {header, body, query, path} and required
    not None. Search the section's page lines for a line where row_tokens(line) returns a
    name equal to field.name.
    - Found: compare req token (T->True, F->False) with field.required, and the type token
      with field.type_raw (case-insensitive). Any mismatch: V2_ROW_MISMATCH (extraction,
      error), with evidence = that line, cited at its page.
    - Not found: V2_ROW_NOT_FOUND (category info, severity info). Never an error.
V2c If field.enum is set: every enum value must appear in norm(enum_citation.quote) when
    enum_citation is set, else in norm(citation.quote). Otherwise V2_ENUM_NOT_GROUNDED.
V2d Sample verbatim check (catalog row V2_SAMPLE_NOT_VERBATIM):
    split sample.raw into non-empty lines, norm each, and require that they appear IN ORDER
    as substrings of the normalized section lines (a subsequence match; this tolerates page
    footers between lines). Otherwise V2_SAMPLE_NOT_VERBATIM (extraction, error), with a hint
    naming the first unmatched line.
V3  Samples (category sample_conflict unless noted):
    - Request sample: json.loads(raw.strip()) strictly. On failure: V3_SAMPLE_UNPARSEABLE.
    - Build a JSON Schema (Draft 2020-12) from the body fields whose names have no "." or "[":
      properties with the mapped type (unknown -> {}), "enum" when present,
      required = names with required True, additionalProperties True.
      Validate with Draft202012Validator.iter_errors, sorted by path:
        validator "required" -> V3_REQUIRED_MISSING (warning)
        validator "type"     -> V3_TYPE_MISMATCH (error)
        validator "enum"     -> V3_ENUM_VIOLATION (error)
    - Top-level sample keys not among the contract body field names: V3_UNKNOWN_FIELD
      (category info, severity info).
    - Response sample: parse the same way (V3_SAMPLE_UNPARSEABLE on failure). If it is an
      object with a "data" key, validate data (each element if data is a list) against the
      fields with location "response", using the same mapping.
    - Never apply format checks; placeholder values like {{host}}, masked tokens and
      example@*.com must raise no issue (SMP-007).
V4  If kind == "endpoint": compare normalized method/path with the section index hints:
    normalize by uppercasing the method; for the path, ensure a leading "/", drop the query,
    strip a trailing "/", and replace ":name" and "{name}" segments with "{}".
    Mismatch: V4_METHOD_MISMATCH / V4_PATH_MISMATCH.
V5  Coverage: in the section text, collect row_tokens names from lines between the table
    headers ("Request Header", "Request Body", "Query Parameters", "Path Parameters",
    "Response Body") and the next header or sample marker. Every collected name absent from
    the contract (fields + definitions): V5_COVERAGE_GAP (extraction, error). Grounded
    contract fields that were not detected as rows are NOT flagged (STR-006).

ENGINE
verify/engine.py: verify_section(contract_path, pages, sections, index_entry) ->
VerificationResult. Issues are sorted by (rule order, field or "", code). The counts are
items, grounded, row_checked, row_ok, samples, samples_parsed.
Write artifacts/verification/<id>.json and also <id>_attempt<n>.json (n =
extraction.attempt). Append manifest records.
CLI verify: --section (multiple), --chapter N, --all (default), --report-only (always exit
0). Print one status line per section plus a totals line. Exit 1 if any section has
extraction-category errors, unless --report-only.

FIXTURES
- FX-02: hand-write correct contracts for synthetic sections S-2.1..S-2.4 in
  tests/fixtures/contracts_good/. Every quote must be copied from the synthetic PDF's
  extracted text. Write a helper test that asserts FX-02 itself has zero extraction issues.
- FX-03: conftest.mutate(contract_dict, kind) with the kinds fabricate_quote, wrong_page,
  flip_required, flip_type, drop_field, enum_not_grounded, repair_sample, wrong_path,
  wrong_method, short_quote, name_not_in_quote. repair_sample changes "Grean" to "Green" in
  the raw sample only; it must yield V2_SAMPLE_NOT_VERBATIM.

TESTS FIRST
tests/unit/test_grounding.py (VER-001..013), test_samples.py (SMP-001..009),
test_structure.py (STR-001..006); tests/integration/test_verify_engine.py (ENG-001..005, with
ENG-004 parametrized over every FX-03 kind -> exactly one expected extraction code).
VER-013 = repair_sample gives V2_SAMPLE_NOT_VERBATIM (already specified in docs/TEST_PLAN.md).
SMP-009 golden file: tests/fixtures/golden/schema_S-2.2.json. Generate it once, inspect it,
and commit it.

SUBAGENTS (use them; this is also evidence of Bob 2.0 subagent use)
- Subagent A: verify/samples.py + tests/unit/test_samples.py + the SMP-009 golden. Return
  only the file list and its pytest summary line.
- Subagent B: verify/grounding.py + tests/unit/test_grounding.py. Same return format.
- You (main): structure.py, engine.py, CLI wiring, FX-02, FX-03, integration tests, and
  merging.

CONSTRAINTS
- No LLM, no network, and no randomness in verify/. rapidfuzz is only for hints.
- Do not modify src/specproof/models/ except to add IssueCode values; if you do, update
  test_models accordingly.
- Do not weaken any test to make it pass.

ACCEPTANCE CRITERIA
- make check green with coverage >= 85%. Paste the final 5 lines.
- ENG-004 shows one passing case per mutation kind (paste the pytest -k ENG_004 -v output).
- `specproof verify --report-only` runs on an empty artifacts/contract/ without crashing.

STOP CONDITIONS
Three failed attempts on the same error: review/BLOCKED.md, then stop.

OUTPUT
SESSION SUMMARY, including which subagents ran and what each returned.
```

## V: Ask mode
```text
Run `pytest -k "ENG_004 or VER_012 or VER_013" -v` and `make check`. Paste both outputs verbatim.
```
