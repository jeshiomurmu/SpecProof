---
name: sp-loop
description: Run one bounded self-correction iteration over failed sections (SpecProof)
metadata:
  user-invocable: true
  disable-model-invocation: true
---

Use the Spec Auditor mode and the specproof-extract skill.
1. Run `specproof loop-status --json` to get the sections with status NEEDS_RETRY (attempt < 3).
2. For each one, read artifacts/feedback/<section_id>.md and fix ONLY the listed items.
   Use subagents in parallel when there are more than 4 sections.
3. Run `specproof verify` on the touched sections, then `specproof classify`.
4. Report the before/after counts exactly as printed: VERIFIED, VERIFIED_WITH_SPEC_FINDINGS,
   NEEDS_RETRY, QUARANTINED.
Never edit src/, tests/, eval/ or sources/. Run `make guard` at the end and report its result.
