# CLAUDE.md: Instructions for Claude Code in the SpecProof repo

@AGENTS.md

## Your role: engine builder (changed 2026-09-25 by the human)

The human decided on 2026-09-25 (about 22:20 BST, after kickoff) that Claude Code builds the deterministic engine task cards (T01–T06, T09–T12), following `prompts/T0X-*.md` and AGENTS.md. Extraction (T07–T08) and the `spec-auditor` mode remain IBM Bob's work.

**You MAY:**
- Implement engine task cards test-first, per AGENTS.md §6–§7.
- Commit each finished task once its checks are green (approved by the human 2026-09-26), using Conventional Commits messages. Never push without asking.
- Run `make check`, `make eval`, `make guard`, and read-only commands.

**You MUST NOT:**
- Modify `artifacts/contract/**`. Extraction happens in Bob's `spec-auditor` mode.
- Modify `eval/thresholds.yaml`, `sources/sources.lock.yaml`, or `.bob/**`.
- Review your own work as if it were independent. Self-review is not a second opinion.

**After every session:** append one row to `docs/AI_USAGE_LOG.md` covering date and time, task, what you did, and the files touched.

## Review checklist (use for every REVIEW_T0X.md)
1. Does any code path let an LLM decide a verification outcome? (Must be no.)
2. Are outputs deterministic? Look for unsorted sets and dicts, timestamps inside hashed content, and ordering by filesystem.
3. Do tests assert behavior, or are they tautological? Would a broken implementation still pass?
4. Any network access outside `specproof fetch`? Any committed third-party full text?
5. Do reason codes match the catalog in `docs/TECHNICAL_ARCHITECTURE.md` §6 exactly?
6. Is any metric computed with a hidden denominator or rounded upward?
