# Engineering rules (all modes)

- Follow AGENTS.md. If this file and AGENTS.md conflict, AGENTS.md wins.
- Test-first: write tests named with their TEST_PLAN IDs before implementing.
- Run `make check` before declaring any task done. Paste its final summary line verbatim.
- Never weaken, skip or delete tests. Never edit eval/thresholds.yaml.
- Determinism: sort collections before serializing, and keep content free of timestamps.
- Keep diffs small and focused on the current task card. Record out-of-scope ideas in review/IDEAS.md.
