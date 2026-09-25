# T06: Loop, classifier, feedback, guard

Est. 75 min · Modes: Plan → Agent · Tests: LOOP-001..010, GRD-001..002, CLI-003
Pre-flight: `git rev-parse HEAD > .specproof_task_base && make check`
After the task: optional Claude Code review (CC-1)

## P: Plan mode
```text
Task T06. Read docs/TECHNICAL_ARCHITECTURE.md sections 5.6, 7 and ADRs 005-006,
docs/LOOP_ENGINEERING.md (Loop B + the feedback file contract), docs/TEST_PLAN.md
LOOP/GRD rows, and AGENTS.md section 8. Plan in at most 20 lines. No edits.
```

## A: Agent mode
```text
ROLE
Lead engineer on SpecProof. AGENTS.md is binding. Test-first.

TASK
T06: implement classification, the self-correction loop plumbing, spec findings, feedback
files, and the reward-hacking guard.

DELIVERABLES
1. loop/classify.py
   classify(result: VerificationResult, contract: ContractSection,
            previous: VerificationResult | None) -> tuple[SectionStatus, list[Finding]]
   - Extraction errors = issues with category "extraction" and severity "error".
   - Grounded sample conflict (ADR-006): a sample_conflict issue on field F counts as a SPEC
     finding only if all hold: F has no extraction-category issue; F's citation (and
     enum_citation, if the conflict is an enum violation) is grounded; the sample citation
     is grounded; the section has zero extraction errors.
   - Status:
       0 extraction errors, 0 grounded conflicts  -> VERIFIED
       0 extraction errors, >=1 grounded conflict -> VERIFIED_WITH_SPEC_FINDINGS
       >0 extraction errors, attempt < 3          -> NEEDS_RETRY
       >0 extraction errors, attempt == 3         -> QUARANTINED
     Early stop: if previous exists and the extraction error count did not strictly
     decrease, return QUARANTINED, even when attempt < 3.
   - Finding mapping:
       V3_ENUM_VIOLATION, V3_TYPE_MISMATCH -> SPEC_SELF_INCONSISTENCY (severity high)
       V3_REQUIRED_MISSING                 -> SPEC_SAMPLE_INCOMPLETE (medium)
       V3_SAMPLE_UNPARSEABLE with a grounded sample citation -> SPEC_MALFORMED_SAMPLE (medium)
     Evidence: every doc citation involved (enum_citation and/or field citation, plus the
     sample citation). IDs via Finding.make_id. review.status = CANDIDATE.
2. loop/feedback.py
   render_feedback(result, contract) -> str in EXACTLY the format of the
   docs/LOOP_ENGINEERING.md example: heading with the attempt transition, the instruction
   line, one "## <field> (location: ...)" block per failing field, sorted, each issue as
   "- CODE: message" plus an evidence or closest-match line. Passing fields must not appear.
   Deterministic output.
3. CLI classify: reads every verification result plus its contract; writes
   artifacts/status.json ({section_id: {status, attempt, extraction_errors}}), writes
   artifacts/findings/spec.json (sorted findings), writes artifacts/feedback/<id>.md for
   NEEDS_RETRY sections, and deletes stale feedback files for terminal sections. Appends
   manifest records.
4. CLI loop-status [--json]: lists sections with status NEEDS_RETRY and attempt < 3.
5. CLI guard [--base REF]: reads .specproof_task_base if --base is not given; runs
   `git diff --name-only <base>` plus untracked files; fails (exit 1) if any path matches
   src/specproof/verify/**, tests/**, eval/thresholds.yaml or sources/sources.lock.yaml,
   and prints the offending paths.
   Guard applies only when .specproof_extraction_task exists (created by the human before
   extraction tasks); otherwise it prints "guard: not an extraction task" and exits 0.
   (This switch is already documented in AGENTS.md section 8.)
6. Downstream exclusion helper: loop/status.py: verified_section_ids(status_path) returns
   only VERIFIED and VERIFIED_WITH_SPEC_FINDINGS (used by T09 and T10; LOOP-010).

TESTS FIRST
tests/integration/test_loop.py: LOOP-001..010, using FX-02 and FX-03 through the real
engine; LOOP-002 must produce exactly one SPEC_SELF_INCONSISTENCY with evidence on synthetic
pages 3 and 5. tests/integration/test_guard.py: GRD-001..002 with the FX-07 tmp git repo.
tests/unit/test_cli.py: add CLI-003.

CONSTRAINTS
Pure logic in classify.py and feedback.py. No LLM. Do not modify verify/ in this task.

ACCEPTANCE CRITERIA
make check green (paste the final 5 lines). Paste the rendered feedback markdown for the
LOOP-003 case.

OUTPUT
SESSION SUMMARY.
```
