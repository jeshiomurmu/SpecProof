---
name: sp-report
description: Build the SpecProof evidence pack and check the eval gate
metadata:
  user-invocable: true
  disable-model-invocation: true
---

Run, in order: `specproof compare --community`, `specproof conform --client artifacts/work/py-unifi-access`,
`specproof report`, `make eval`.
Report: the headline metrics printed by `specproof report` (verbatim), the eval gate result, and
the path of the generated HTML report. Do not edit any file except through these commands.
