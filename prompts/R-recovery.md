# Recovery prompts (use only when something goes wrong)

## R1: `make check` still red after the task
Mode: Agent
```text
make check is failing. Here is the output: <<EDIT: paste the last 40 lines>>.
1. Classify each failure: lint, type, test assertion, test error, or coverage.
2. For each failing test, state in one line whether the TEST encodes the spec in
   docs/TEST_PLAN.md correctly. If a test contradicts the spec, STOP and write
   review/BLOCKED.md. Do not change the test.
3. Fix the implementation only. Re-run make check.
Stop after 3 attempts on the same failure and write review/BLOCKED.md (error, attempts,
hypothesis, smallest reproducer).
```

## R2: Bob drifted out of scope (touching files outside the task card)
Mode: Agent
```text
Stop. You modified files outside task <<EDIT: T0X>>: <<EDIT: list from `git status`>>.
Revert every change outside the deliverables listed in prompts/<<EDIT: file>>
(git checkout -- <path> for tracked files; delete new files that are out of scope). Record
any useful idea in review/IDEAS.md instead. Then show `git status` and continue the task
card from where it was correct.
```
If the damage is large: use Bob's **checkpoint rollback** to the start of the task instead, then restate the A prompt.

## R3: Bob claimed a result without showing command output
Mode: Ask
```text
You stated "<<EDIT: the claim>>" but I don't see command output supporting it in this
session. Per .bob/rules/02-truthfulness.md: run the command that proves it and paste the
raw output. If it doesn't support the claim, retract the claim explicitly.
```

## R4: Context is getting long / Bob is losing the thread (hand off to a fresh task)
Mode: Ask (in the OLD task)
```text
Write review/HANDOFF_<<EDIT: T0X>>.md for a fresh session, containing: the task goal; what
is done (files + test IDs green); what remains (a checklist); the exact failing command and
its last output if any; decisions made and why; files not to touch. At most 40 lines.
Facts only.
```
Then start a new Bob task with `00-session-bootstrap.md` plus: `Also read review/HANDOFF_<<T0X>>.md and continue from "what remains".`

## R5: Extraction not converging (the same section fails twice with the same codes)
Mode: Ask (diagnose; no edits)
```text
Section <<EDIT: S-x.y>> failed verification in consecutive attempts. Read
artifacts/verification/<<id>>_attempt1.json, _attempt2.json and artifacts/feedback/<<id>>.md.
Then read pages <<EDIT: range>> of artifacts/work/spec.pdf and
artifacts/work/sections.jsonl for this id.
Diagnose in at most 10 lines which of these it is:
(a) extraction error Bob keeps repeating;
(b) a layout-extraction artifact (text differs from the visual PDF: broken line, merged
    columns);
(c) a verifier limitation (rule too strict for this layout);
(d) a genuine document defect.
Quote the evidence for your diagnosis.
```
- (a) → let the classifier quarantine it; it's honest.
- (b) or (c) → **do not change the verifier during extraction.** Note it in `review/IDEAS.md` and in the report's limitations section. If it affects many sections, open a new Loop A task (`T05b`) with a test that reproduces it, then re-verify.
- (d) → it will surface as a spec finding once both sides are grounded.

## R6: `specproof guard` failed
```text
guard reports protected paths changed: <<EDIT: paths>>. This task is an extraction task and
must not touch them. Revert those paths to the task base
(git checkout $(cat .specproof_task_base) -- <paths>), re-run specproof guard, and paste the
output.
```

## R7: A test is genuinely wrong (it contradicts the architecture or the TEST_PLAN)
Human decision. Update `docs/TEST_PLAN.md` **first** with the reason, in its own commit (`T0X: test-plan correction: <reason>`), and only then change the test. This keeps the git history honest about why a test changed.
