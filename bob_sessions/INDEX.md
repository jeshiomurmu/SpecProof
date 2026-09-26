# IBM Bob 2.0 session evidence

Only the tasks below ran in IBM Bob 2.0. The deterministic engine (T01–T06, T09–T12, T14) was built with Claude Code, and after the Bob allowance ran out during T08, Claude Code finished the extraction. Contracts record their real author in `producer`, and `docs/AI_USAGE_LOG.md` logs every session.

| Task | Goal | Bob mode(s) | Bob 2.0 features used | Export | Screenshot | Commit |
|---|---|---|---|---|---|---|
| T07 | Extraction pilot (S-3.2, S-4.1, S-4.2) | `spec-auditor` | Custom mode, skill, `/sp-extract`, PDF reading | exports/T07.md | screenshots/T07.png | `68ba261` |
| T08 (partial) | Chapter 4 attempt 1 (S-4.3 to S-4.14) | `spec-auditor` | Custom mode, skill, PDF reading | none (the human could not export it) | none (the human could not take one; none was fabricated) | `98f4962` |

## Feature coverage summary
| Bob 2.0 feature | Tasks where it was used |
|---|---|
| Custom mode `spec-auditor` + skill + `/sp-*` commands | T07, T08 (partial) |
| Document understanding (PDF) | T07, T08 (partial) |
| Subagents, parallel tasks | not used: the allowance ran out first |
