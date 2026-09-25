# T08: Full extraction with subagents, parallel tasks, and the bounded loop

Est. 3–4 h wall-clock (mostly waiting) · Mode: **Spec Auditor** · Bobcoin tier: Extraction
Pre-flight:
```bash
git rev-parse HEAD > .specproof_task_base
touch .specproof_extraction_task
specproof loop-status          # pilot sections should already be terminal
python -c "import json,collections;d=json.load(open('artifacts/sections_index.json'));print(collections.Counter((x['chapter'],x['kind']) for x in d if x['kind']!='overview'))"
```
Use the chapter counts to decide batching. Order of value: chapter 4 first (it contains F7), then chapter 3, then the rest.

**Evidence to capture while this runs:** a screenshot of the subagent fan-out (`bob_sessions/screenshots/T08-subagents.png`), a screenshot of parallel/background tasks (`T08-parallel.png`), and one export per chapter task.

## O1: Spec Auditor mode (chapter orchestrator; one Bob task per chapter or group of chapters)
```text
ROLE
You are the Spec Auditor orchestrator for SpecProof. The specproof-extract skill is binding.
You coordinate subagents; the deterministic verifier decides correctness.

TASK
T08: extract every schema and endpoint section of chapter(s) <<EDIT: e.g. 4>> from
artifacts/work/spec.pdf.

STEP 1 - Inventory
From artifacts/sections_index.json, list this chapter's sections with kind "schema" or
"endpoint": id, title, pages. Skip any section whose artifacts/status.json status is
VERIFIED or VERIFIED_WITH_SPEC_FINDINGS.

STEP 2 - Schema sections first (you, not a subagent)
Extract the chapter's schema section(s) yourself. Endpoint sections reference their enums.

STEP 3 - Delegate endpoint sections to subagents
Split the remaining endpoint sections into batches of at most 8 consecutive sections. Start
one subagent per batch, IN PARALLEL where possible. Give each subagent this exact brief,
filled in:

  ---- SUBAGENT BRIEF ----
  You extract API contract sections for SpecProof. Read and follow
  .bob/skills/specproof-extract/SKILL.md exactly.
  Sections: <ids>. Page ranges: <id: start-end, ...>.
  Source: artifacts/work/spec.pdf. Read ONLY those pages. Schema enums for this chapter
  are defined in <schema id> on page(s) <n>; cite them via enum_citation.
  Write one file per section: artifacts/contract/<id>.json, following
  docs/schemas/contract.schema.json.
  extraction = {"producer":"ibm-bob","mode":"spec-auditor","prompt_version":"<current>",
                "attempt":1,"bob_task_ref":"T08-ch<n>"}
  Copy samples character-for-character; never fix typos; never open any other spec of this
  API; never write outside artifacts/contract/.
  When done, run: specproof verify --section <id> ... --report-only
  Return ONLY: the list of files written, and the verify totals line verbatim.
  ---- END BRIEF ----

STEP 4 - Collect
When all subagents return, run:
  specproof verify --chapter <n> --report-only
  specproof classify
  specproof loop-status
  specproof guard

HARD RULES
Never re-extract terminal sections. Never edit anything outside artifacts/contract/. Never
claim results you did not see in command output.

OUTPUT
- A per-batch table: subagent, sections, files written, verify totals (verbatim)
- The classify and loop-status output, verbatim
- The guard output, verbatim
- SESSION SUMMARY (list how many subagents ran and whether they ran in parallel)
```

## O2: The loop (run after all chapters are extracted; at most twice)
Use the `/sp-loop` command, or paste this:
```text
Run one bounded self-correction iteration for SpecProof, following the specproof-extract
skill.
1. `specproof loop-status --json`: these are the sections to retry (NEEDS_RETRY, attempt < 3).
2. If there are more than 4, split them into batches of up to 6 and use parallel subagents.
   Each subagent gets the SUBAGENT BRIEF from prompts/T08-extraction-full.md, plus:
   "This is a RETRY. First read artifacts/feedback/<id>.md. Fix ONLY the items listed there.
   Keep every other item byte-identical. Set extraction.attempt to the previous value + 1."
3. Run: specproof verify --section <all retried ids> --report-only; specproof classify;
   specproof loop-status; specproof guard.
4. Report the status counts BEFORE and AFTER this iteration (VERIFIED,
   VERIFIED_WITH_SPEC_FINDINGS, NEEDS_RETRY, QUARANTINED), copied from command output.
```
Run O2 a second time only if `loop-status` still lists sections. After the second iteration, every section is terminal by construction.

## O3: Ask mode (closeout)
```text
Run:
  specproof classify
  python -c "import json,collections;s=json.load(open('artifacts/status.json'));print(collections.Counter(v['status'] for v in s.values()))"
  pytest -m real_source -k E2E_R01 -v
  specproof guard
Paste all outputs verbatim. Then list every QUARANTINED section with its last 3 issue codes,
read from artifacts/verification/<id>.json.
```

**After T08:** `rm .specproof_extraction_task`, run `make check`, commit `T08: extraction complete (loop x<n>)`, export each chapter task, save the screenshots, add INDEX rows.

**If Bobcoins run low:** stop starting new chapters once coverage in `status.json` reaches ≥ 0.90 of endpoint sections, and spend the rest on O2. Record the actual state honestly; see IMPLEMENTATION_PLAN §2.
