---
name: sp-verify
description: Run deterministic verification and summarize results (SpecProof)
metadata:
  user-invocable: true
  disable-model-invocation: true
---

Run `specproof verify` (with `--chapter` or `--section` if I gave one), then `specproof loop-status`.
Report the printed status table verbatim. Then list the top 5 failure reason codes with counts.
Do not modify any files in this task.
