# Session evidence rules (all modes)

At the end of every task, output a block titled SESSION SUMMARY containing:
- Task card ID and one-line goal
- Files created or modified
- Commands run and their final result lines
- Bob features used (Plan, Agent, subagents, parallel/background tasks, document reading, checkpoints)
- Anything left undone

Then remind the human to: (1) export this task's history to bob_sessions/exports/<task-id>.md,
(2) screenshot the consumption summary to bob_sessions/screenshots/<task-id>.png,
(3) add a row to bob_sessions/INDEX.md.
