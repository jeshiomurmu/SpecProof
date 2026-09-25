# T09: OpenAPI export and community-spec comparison

Est. 60 min · Modes: Plan → Agent · Tests: CMP-001..008
Pre-flight: `git rev-parse HEAD > .specproof_task_base && make check`

## P: Plan mode
```text
Task T09. Read docs/TECHNICAL_ARCHITECTURE.md sections 3 (S6), 5.6 (COMMUNITY_* types) and
ADR-003, docs/TEST_PLAN.md CMP rows and FX-05, and docs/DATA_GOVERNANCE_AND_LINEAGE.md
section 7 (neutral wording). Plan in at most 15 lines. No edits.
```

## A: Agent mode
```text
ROLE
Lead engineer on SpecProof. AGENTS.md is binding. Test-first.

TASK
T09: export verified contracts to OpenAPI 3.1, and diff them field-by-field against the
community OpenAPI conversion. Every discrepancy is backed by OUR citation to the PDF.

DELIVERABLES
1. compare/paths.py: normalize_path(p): ensure a leading "/", drop the query, strip a
   trailing "/", replace ":name" and "{name}" segments with "{}". Reuse it in verify/
   ONLY IF the logic is identical there; otherwise leave verify/ untouched and duplicate the
   minimal logic here. (Changing verify/ is out of scope.)
2. compare/openapi_export.py: export(contracts, status) -> dict
   - Include only sections from loop.status.verified_section_ids (LOOP-010, CMP-002).
   - paths[path_with_{param}_names][method.lower()]: summary = title,
     x-specproof-section = id, parameters (header, path, query), requestBody
     (application/json schema built exactly like verify/samples.py builds it),
     responses."200" with a data schema when response fields exist.
   - components.schemas from schema sections (definitions).
   - Validate with openapi_spec_validator.validate before writing
     artifacts/openapi.specproof.yaml (sorted keys). Exit 1 if invalid.
3. compare/community.py: diff(ours, theirs) -> list[Finding]
   - Match operations on (METHOD, normalize_path(path)). CMP-003: slash-less and
     parameter-renamed paths must match.
   - For every matched operation, compare request body properties:
       required set difference   -> COMMUNITY_REQUIRED_MISMATCH (per field)
       type difference           -> COMMUNITY_TYPE_MISMATCH
       enum set difference       -> COMMUNITY_ENUM_MISMATCH
       in ours, not theirs       -> COMMUNITY_MISSING_FIELD
       in theirs, not ours       -> COMMUNITY_EXTRA_FIELD (severity info)
   - Operation in ours, absent in theirs -> COMMUNITY_MISSING_ENDPOINT.
   - Resolve $ref in the community spec (a local resolver over components; no network).
   - Evidence: our doc citation (page + quote) for the field, plus a code-kind evidence
     pointing to the community file with a JSON pointer in `snippet`
     (e.g. "#/paths/~1api~1v1~1developer~1users/post/requestBody/...").
   - Message style (neutral): "Community spec marks `size` as required; the PDF row on
     page 5 marks it optional (F)."
4. CLI export-openapi and compare --community (writes artifacts/findings/community.json,
   sorted; appends manifest records).
5. Fixture FX-05 tests/fixtures/community_min.yaml exactly as in TEST_PLAN.

TESTS FIRST
tests/integration/test_compare.py: CMP-001..008.

THEN
Run it on the real data: `specproof export-openapi && specproof compare --community`. Print
counts by finding type and the first 5 findings with their evidence.

CONSTRAINTS
Blind-extraction principle: this task is the FIRST time the community spec is read by the
pipeline. Do not modify artifacts/contract/. Do not modify verify/.

ACCEPTANCE CRITERIA
make check green (final 5 lines); real-data counts by type pasted verbatim.

OUTPUT
SESSION SUMMARY.
```

## V: Ask mode
```text
Run `specproof compare --community` and print the count of findings per type from
artifacts/findings/community.json, plus 3 examples with full evidence. Verbatim only.
```
