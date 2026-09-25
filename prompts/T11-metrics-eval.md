# T11: Metrics, eval gate, audit tooling

Est. 60 min · Modes: Plan → Agent · Tests: MET-001..004, EVL-001..005
Pre-flight: `git rev-parse HEAD > .specproof_task_base && make check`

## P: Plan mode
```text
Task T11. Read docs/EVALUATION_FRAMEWORK.md in full, eval/thresholds.yaml (read-only;
protected), docs/DATA_QUALITY_AND_BIAS.md section 5, and docs/TEST_PLAN.md MET/EVL rows and
FX-06. List every metric key with its exact numerator and denominator source, in at most 30
lines. No edits.
```

## A: Agent mode
```text
ROLE
Lead engineer on SpecProof. AGENTS.md is binding. Test-first. Honesty in numbers is the
whole point of this task.

TASK
T11: compute every metric in docs/EVALUATION_FRAMEWORK.md section 2, gate them against
eval/thresholds.yaml, and implement the blind-audit tooling.

DELIVERABLES
1. report/metrics.py
   - Each rate is stored as {"numerator": int, "denominator": int, "value": float | null}.
     value = numerator / denominator truncated (not rounded) to 4 decimals; null when the
     denominator is 0 (never 0/0 -> 1.0).
   - Implement every key in EVALUATION_FRAMEWORK sections 2.1-2.6 that can be computed from
     artifacts: status.json, verification/*.json (use the *_attempt1.json files for
     first-pass metrics), findings/*.json, eval/audit/*.csv. Keys whose inputs don't exist
     yet (e.g. audited_precision before T13, manual baseline, Bobcoins) are written as
     {"value": null, "reason": "<which input is missing>"}.
   - determinism: read artifacts/determinism.json if present (written by the E2E-002/R03
     tests), else null with a reason.
   - Display helper pct(value) -> "89.9%" using truncation (MET-003).
   - wilson(c, n, z=1.959963984540054) -> (lo, hi) (MET-004 reference values).
   - Write artifacts/metrics.json (sorted keys) plus a manifest record.
2. evalgate.py: gate(metrics, thresholds) -> GateResult. For each threshold key: "min"
   means value >= min; "max" means value <= max. A missing or null metric is a FAIL with the
   reason "missing: <reason>" (EVL-004). Write artifacts/eval_result.json.
   CLI eval: print a table (metric | value | threshold | PASS/FAIL); exit 1 on any FAIL.
3. CLI audit-sample --n 40 --seed 20260926: stratified sampling over ALL contract items
   (including quarantined and row-unchecked ones): 4 per chapter, spread across locations;
   if a chapter has fewer, take all and top up round-robin from other chapters. Use
   random.Random(seed). Write eval/audit/audit_sample.csv with the columns item_id,
   section_id, page, claimed_name, claimed_required, claimed_type, claimed_enum, quote,
   verdict, reason, missed_neighbor (the last 3 empty). Do NOT include verifier status.
   Refuse (exit 1) if the file already exists.
4. CLI audit-score: join audit_sample.csv verdicts with verification results; compute
   audited_precision with Wilson CI, audited_miss_rate, verifier_false_accept; merge them
   into metrics.json. If eval/audit/findings_review.csv exists (columns finding_id,
   status, reviewer, note), set review.status on findings and compute *_confirmed counts.

TESTS FIRST
tests/unit/test_metrics.py (MET-001..004 using FX-06 tests/fixtures/state_metrics.json);
tests/unit/test_evalgate.py (EVL-001..005).

CONSTRAINTS
eval/thresholds.yaml is protected: read it, never write it. No rounding up anywhere.

ACCEPTANCE CRITERIA
make check green (final 5 lines). Run `specproof report` is NOT required yet; run
`python -m specproof.report.metrics` or the CLI path you wired, then `specproof eval`, and
paste the eval table verbatim (FAILs for not-yet-available metrics are expected and fine).

OUTPUT
SESSION SUMMARY.
```
