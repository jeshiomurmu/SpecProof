# Evaluation and Success Metrics Framework: SpecProof

Version 1.0 · 2026-09-25 · The thresholds in `eval/thresholds.yaml` were committed **before** any extraction ran.

## 1. Principles
1. **Every number has a visible denominator.** We write "96/107 (89.7%)", never "~90%".
2. **Never round up.** Truncate to one decimal place.
3. **Report failures too.** Metrics below target are still shown, marked as such.
4. **One source of truth.** `artifacts/metrics.json` feeds the README, report, slides and video script.
5. **Separate what the machine verified from what a human confirmed.** They are labeled differently everywhere.

## 2. Metric catalog

### 2.1 Extraction quality (machine-verified)

| Metric key | Formula | Gate (thresholds.yaml) |
|---|---|---|
| `endpoint_coverage` | endpoint sections with a contract file ÷ endpoint sections in `sections_index.json` | min 0.90 |
| `citation_presence_rate` | items with a citation ÷ all items | must be 1.00 (schema-enforced) |
| `citation_grounding_rate` | items passing V2 ÷ all items | min 0.95 |
| `row_check_applicability` | items with a single-line row found ÷ table items | reported only (bias B3) |
| `row_consistency_rate` | items passing V2b ÷ items where V2b applied | min 0.90 |
| `field_coverage` | detector-found row names present in the contract ÷ detector-found row names | reported |
| `schema_valid_rate` | contract files passing V1 ÷ contract files | reported (expected 1.0) |
| `sample_parse_rate` | document samples parsing as JSON ÷ samples | min 0.80 (a low value means spec defects, which we report) |

### 2.2 Loop effectiveness (the self-correction story)

| Metric key | Formula |
|---|---|
| `first_pass_verified_rate` | sections VERIFIED or VERIFIED_WITH_SPEC_FINDINGS at attempt 1 ÷ sections |
| `final_verified_rate` | same, after the loop ÷ sections (gate min 0.85) |
| `loop_lift` | `final_verified_rate − first_pass_verified_rate` |
| `quarantine_rate` | QUARANTINED ÷ sections (gate max 0.10) |
| `mean_attempts` | mean attempts over all sections |
| `issues_fixed_by_loop` | extraction issues at attempt 1 that are absent in the final state |

### 2.3 Accuracy (human-verified)

| Metric key | Formula |
|---|---|
| `audited_precision` | correct ÷ audited items in the blind sample; reported with *n* and a Wilson 95% CI (gate min 0.90) |
| `audited_miss_rate` | misses noticed by the auditor ÷ audited sections |
| `verifier_false_accept` | audited items the verifier passed but the auditor marked incorrect ÷ verifier-passed audited items (measures the verifier's blind spots honestly) |

### 2.4 Findings (impact)

| Metric key | Formula |
|---|---|
| `spec_findings_candidate` / `spec_findings_confirmed` | count, by type |
| `community_discrepancies_candidate` / `_confirmed` | count, by type; confirmation requires adjudication against the PDF |
| `client_findings_candidate` / `_confirmed` | count, by type; `CLIENT_SAMPLE_REJECTED` is confirmed by re-running the generated test |

### 2.5 Productivity and cost (the brief's "demonstrate impact")

| Metric key | Formula | Source |
|---|---|---|
| `manual_minutes_per_endpoint` | Median over 3 endpoints transcribed by hand with a stopwatch (protocol §5) | `eval/audit/manual_baseline.csv` |
| `specproof_minutes_per_endpoint` | Wall-clock extraction plus loop time ÷ endpoints, taken from Bob task timestamps | T08 exports |
| `time_reduction_factor` | manual ÷ SpecProof, stated with the method and its caveat | computed |
| `bobcoins_per_verified_endpoint` | Bobcoins spent on S3 and loop tasks ÷ verified endpoints | Screenshots |
| `projected_manual_hours_full_spec` | `manual_minutes_per_endpoint × endpoints ÷ 60`, stated as an estimate with its range | computed |

### 2.6 Engineering quality

| Metric key | Gate |
|---|---|
| `determinism` (identical artifact hashes over two runs) | min 1.0 |
| `unit_test_coverage` | min 0.85 |
| `tests_passed` / `tests_total` | all green |

## 3. Success criteria (what "we did it" means)

| Level | Criteria |
|---|---|
| **Minimum viable (must)** | All gates pass; ≥ 1 confirmed spec finding with both citations; live report URL; `bob_sessions` complete |
| **Strong (target)** | `final_verified_rate` ≥ 0.95; `audited_precision` ≥ 0.95 with *n* = 40; `loop_lift` > 0 shown in the funnel; ≥ 1 confirmed client finding with a runnable test |
| **Exceptional (stretch)** | Issue or PR opened upstream with SpecProof evidence; a second document processed |

## 4. Blind audit protocol
1. **Sample.** Run `specproof audit-sample --n 40 --seed 20260926`. The seed is fixed now to prevent cherry-picking. Sampling is stratified: 4 items per chapter, spread across locations (header, body, response, schema), drawn from **all** items, including quarantined and row-unchecked ones.
2. **Sheet.** The command writes `eval/audit/audit_sample.csv` with the columns `item_id, section_id, page, claimed_name, claimed_required, claimed_type, claimed_enum, quote`. The verifier status is **not** included.
3. **Judge.** Open the PDF at `page` and mark `verdict ∈ {correct, incorrect}` and `reason` (free text). Also note any obvious miss in the same table (`missed_neighbor`).
4. **Optional second auditor.** Claude Code runs the same sheet independently. Record both verdicts and report the agreement rate.
5. **Compute.** Run `specproof audit-score`, which joins verdicts with statuses and computes `audited_precision`, the Wilson CI and `verifier_false_accept`.
6. **Freeze.** Commit the CSV. Never re-draw the sample.

## 5. Manual baseline protocol
1. Choose 3 endpoint sections **before looking at SpecProof output**: one small (e.g. §3.8 Unassign NFC Card), one medium (§3.2 User Registration) and one large (§4.2 Create Visitor).
2. Start a stopwatch. Transcribe each into a spreadsheet (fields, required, type, enum, plus a sample check). Stop when done.
3. Record minutes per endpoint in `eval/audit/manual_baseline.csv`. Take the median.
4. State the caveats in the report: single tester, the tester is the builder, and there is a learning effect.

## 6. Eval gate
`make eval` = `specproof eval --thresholds eval/thresholds.yaml`
- Exits 0 only if every `min` and `max` passes. Writes `artifacts/eval_result.json` with each metric, its threshold, and pass/fail.
- Run before recording the demo and before submission. **Never** edit thresholds to pass (protected path; `make guard`).

## 7. Reporting templates (copy exactly; fill from `metrics.json`)
- Coverage: "SpecProof extracted **{a}/{b}** endpoint sections ({pct}%)."
- Grounding: "**{g}/{n}** contract items have a citation found verbatim on the cited page."
- Loop: "First pass: {fp}% of sections verified. After the self-correction loop: {final}%."
- Accuracy: "Blind audit of {n} random items: {c}/{n} correct ({pct}%, 95% CI {lo}–{hi}%)."
- Impact: "Manual transcription took a median {m} min per endpoint (n=3, single tester). SpecProof: {s} min per endpoint."
