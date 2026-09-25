# Claude Code prompts (reviewer / red-team / second auditor ONLY)

Run in Bob IDE's integrated terminal: `cd specproof && claude`. CLAUDE.md is loaded automatically and restricts your role. After each use, append a row to `docs/AI_USAGE_LOG.md`.

## CC-1: Adversarial review of a Bob task (after T05, T06, T10)
```text
Review the changes of task <<EDIT: T05>>: run `git diff $(cat .specproof_task_base) --stat`
and read the full diff. Apply every item of the review checklist in CLAUDE.md. Additionally:
1. Try to break the verifier: for each rule, describe one concrete contract mutation that
   would PASS verification while being wrong. For each, say whether an existing test covers
   it (cite the test ID) or not.
2. Check that no code path in src/specproof/verify/ depends on rapidfuzz scores, randomness,
   time, dict ordering, or the filesystem listing order.
3. Run make check and paste the summary.
Write the findings to review/REVIEW_<<T05>>.md as a table: severity (blocker / major /
minor), file:line, issue, suggested test (TEST_PLAN-style ID with an "ADV-" prefix), and a
suggested fix in prose.
Do NOT modify src/, tests/, artifacts/, eval/ or .bob/.
```
Hand the blocker/major rows to Bob as a follow-up Agent task: `Implement the fixes for review/REVIEW_T05.md rows <n>, test-first; add the ADV- tests under tests/adversarial/.`

## CC-2: Fresh-clone reproducibility (T14)
```text
In a temporary directory outside this repo: git clone <<EDIT: repo URL>> sp-repro && cd sp-repro.
Run make setup, make fetch, make pipeline, make eval, make test-e2e, with the timing of each.
Then compare the sha256 of every file under artifacts/ that is tracked by git between
sp-repro and the original repo, and list any differences. Write the results to
review/REPRO_REPORT.md in the original repo (commands, timings, pass/fail, hash
differences). Modify nothing else.
```

## CC-3: Independent second auditor (T13)
```text
Copy eval/audit/audit_sample.csv to eval/audit/audit_sample_cc.csv. For each row, open
artifacts/work/spec.pdf at `page` (use `pdftotext -layout -f N -l N`, and rasterize the page
if the text looks garbled) and decide whether claimed_name, claimed_required, claimed_type and
claimed_enum all match the document. Fill verdict (correct|incorrect), reason, and
missed_neighbor in audit_sample_cc.csv ONLY. Do not open artifacts/verification/ or
the original sheet's verdict columns. Report your count of correct items.
```

## CC-4: Claims check before submitting (T15)
```text
Read review/SUBMISSION_DRAFT.md, review/VIDEO_SCRIPT.md and review/SLIDES_OUTLINE.md.
Extract every numeric or factual claim. For each claim, check it against
artifacts/metrics.json, artifacts/findings.json, eval/audit/findings_review.csv and
docs/VERIFIED_FACTS.md. Output review/CLAIMS_CHECK.md as a table: claim, location, source
found (file + key), status (SUPPORTED / MISMATCH / UNSUPPORTED / ROUNDED-UP). Flag any
finding mentioned that is not CONFIRMED. Modify nothing else.
```
