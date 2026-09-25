---
description: Extract cited contracts for one chapter of the spec (SpecProof)
argument-hint: <chapter number, e.g. 4>
---
Use the Spec Auditor mode and the specproof-extract skill.

Extract every section of the chapter number I give after this command:
1. Read artifacts/sections_index.json and list that chapter's sections (schema sections first).
2. Extract the schema section(s) yourself, then delegate the endpoint sections to subagents
   (one subagent per ~8 sections), each following the skill exactly and reading only its page range.
3. When all subagents finish, run: specproof verify --chapter <n>
4. Report: sections written, the verify status counts exactly as printed, and the IDs that failed.
Do not re-extract anything already VERIFIED. Do not touch files outside artifacts/contract/.
