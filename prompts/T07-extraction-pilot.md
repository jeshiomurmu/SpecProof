# T07: Extraction pilot (validate mode, skill and PDF reading on 3 sections)

Est. 30 min · Mode: **Spec Auditor** (custom mode) · Bobcoin tier: Extraction (keep it small)
Pre-flight (terminal):
```bash
git rev-parse HEAD > .specproof_task_base
touch .specproof_extraction_task      # turns on the reward-hacking guard
make check && specproof segment && ls artifacts/work/spec.pdf
```

## E1: Spec Auditor mode (extract)
```text
ROLE
You are the Spec Auditor for SpecProof. Follow the specproof-extract skill
(.bob/skills/specproof-extract/SKILL.md) exactly. The deterministic verifier, not you,
decides correctness.

TASK
T07 pilot: extract three sections from artifacts/work/spec.pdf: S-4.1 (Schemas), S-3.2
(User Registration), S-4.2 (Create Visitor). This pilot tests whether the skill and your
PDF reading produce verifiable contracts before we scale to all sections.

INPUTS
- artifacts/sections_index.json: take page_start/page_end, method_hint and path_hint for
  the three IDs.
- artifacts/work/spec.pdf: read ONLY those page ranges.
- The contract schema: docs/schemas/contract.schema.json (field names are exact).

PROCEDURE
1. For each section, print its index entry first.
2. S-4.1 is a schema section: write definitions[] (kind "schema"), one FieldSpec per
   documented attribute. For enums written like "enum reason {A,B,C}", copy the values
   EXACTLY and cite that line.
3. S-3.2 and S-4.2 are endpoint sections: method, path and permission_key exactly as
   printed. One FieldSpec per table row (header and body; response fields if listed).
   Quotes are verbatim substrings (12-200 characters) containing the field name,
   preferably the whole row line. For visit_reason in S-4.2, set enum and enum_citation
   from S-4.1 (page 52).
4. Samples: copy the request JSON inside --data-raw '...' and the Response Sample JSON
   character-for-character, line by line, WITHOUT fixing anything. Typos such as
   "Interviemw" and "Fist Name" must be preserved exactly. Give each sample a citation
   quote from inside it.
5. extraction = {"producer": "ibm-bob", "mode": "spec-auditor",
   "prompt_version": "extract-v1", "attempt": 1, "bob_task_ref": "T07"}
6. Write artifacts/contract/S-4.1.json, S-3.2.json, S-4.2.json.
7. Run: specproof verify --section S-4.1 --section S-3.2 --section S-4.2 --report-only
   Then: specproof classify
   Then: specproof guard

HARD RULES
- Do not open artifacts/work/community_openapi.yaml or any other spec of this API.
- Do not edit anything outside artifacts/contract/.
- Do not say a section is correct. Report the verifier's output only.

OUTPUT
1. The verify and classify output, verbatim.
2. For each section: status, extraction error count, and the list of issue codes.
3. The guard output, verbatim.
4. SESSION SUMMARY.
```

## E2: Spec Auditor mode (retry, if any section is NEEDS_RETRY)
```text
Run `specproof loop-status --json`. For each listed section, read
artifacts/feedback/<section_id>.md and fix ONLY the items listed there, following the
specproof-extract skill. Set extraction.attempt to the previous value + 1. Do not change any
item not listed in the feedback. Then run verify (--report-only) for those sections, then
classify, then guard, and paste all three outputs verbatim.
```

## Human decision gate (do NOT skip)
Expected: **S-3.2 → VERIFIED** and **S-4.2 → VERIFIED_WITH_SPEC_FINDINGS**, with a `SPEC_SELF_INCONSISTENCY` for `visit_reason` citing pages 52 and 56.

| Outcome | Action |
|---|---|
| As expected (possibly after one retry) | Proceed to T08 |
| Repeated `V2_CITATION_NOT_FOUND` | Bob's quotes are drifting from the page text. Use prompt E3 to tighten the skill, then re-pilot |
| Repeated `V2_SAMPLE_NOT_VERBATIM` | Bob is "cleaning" samples. Use E3 with emphasis on samples |
| `V5_COVERAGE_GAP` | Bob skipped rows. Use E3 with "one FieldSpec per row, including wrapped rows" |
| Wrong page numbers | Bob is counting pages differently. Use E3, telling it to use `sections_index.json` ranges and cite the page where the quote physically appears |

## E3: Agent mode (skill repair, only if the gate failed)
```text
The T07 pilot produced these recurring verifier issues: <<EDIT: paste codes + 2 examples>>.
Edit .bob/skills/specproof-extract/SKILL.md to prevent exactly these failure modes: add
precise do/don't instructions and one worked example drawn from the failing case, using the
real quote from the page. Bump prompt_version to "extract-v2" everywhere it appears in the
skill. Do not change any other file. Show the diff.
```
Then delete the three contract files and re-run E1 with `extract-v2`.

**After T07:** `rm .specproof_extraction_task`, run `make check`, commit `T07: extraction pilot`, then export, screenshot and add an INDEX row.
