# Production prompts: how to use them

Every task has one file. Each file contains copy-paste blocks meant to be run **in order**:

| Block | Mode | Purpose |
|---|---|---|
| **P** | Plan | Bob reads the context and commits to a plan. Cheap; no edits. |
| **A** | Agent | Implementation, test-first. The main work. |
| **V** | Ask | Bob reports the verification output verbatim. Cheap. |
| **R** | per `R-recovery.md` | Only when something goes wrong. |

## Rules for using the prompts
1. **Pre-flight every task** in the terminal: `git rev-parse HEAD > .specproof_task_base && make check`. From T02 on, a green baseline is required before you start.
2. **One task = one Bob task (conversation).** Start a new Bob task for every card, and begin it with `00-session-bootstrap.md`. This keeps context small (fewer Bobcoins) and makes each session export clean evidence.
3. **Paste the blocks unchanged.** They reference exact file paths, test IDs and reason codes that the rest of the kit depends on. Only edit the lines marked `<<EDIT>>`.
4. **Wait for the SESSION SUMMARY** (defined in `.bob/rules/03-session-evidence.md`) before committing.
5. **After each task:** `make check && specproof guard`, then commit `T0X: …`, export the session to `bob_sessions/exports/T0X.md`, save a screenshot to `bob_sessions/screenshots/T0X.png`, and add an INDEX row.

## Files
| File | Task |
|---|---|
| `00-session-bootstrap.md` | First message of every new Bob task |
| `T01-scaffold.md` … `T15-submission.md` | Task cards T01–T15 |
| `R-recovery.md` | Failure-recovery prompts (red checks, drift, fabricated claims, rollback, context handoff, non-converging extraction) |
| `CC-claude-code.md` | Claude Code prompts (reviewer / red-team / second auditor only) |

## Prompt anatomy (every A block follows this shape)
ROLE → TASK → READ FIRST → DELIVERABLES → METHOD (test-first steps) → CONSTRAINTS → ACCEPTANCE CRITERIA → STOP CONDITIONS → OUTPUT FORMAT.
Plain text works better than clever phrasing here: explicit paths, explicit IDs, explicit "do not" lists.
