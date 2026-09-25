# Data Quality and Bias Assessment: SpecProof

Version 1.0 · 2026-09-25 · This document covers the quality of the **input** (the spec document), the quality of the **output** (extracted contracts and findings), and the **biases** that could distort either one or distort how we evaluate them.

## 1. Quality dimensions and controls

| Dimension | Definition for SpecProof | Control | Metric (see EVALUATION_FRAMEWORK) |
|---|---|---|---|
| Accuracy | Extracted items say what the document says | V2 grounding, V2b row check, V2c enum grounding; blind hand audit | `citation_grounding_rate`, `row_consistency_rate`, `audited_precision` |
| Completeness | Every endpoint and every table row is captured | Deterministic segmenter as the endpoint oracle; V5 row detector as the field oracle | `endpoint_coverage`, `field_coverage` |
| Consistency | The document agrees with itself; our contract agrees with the document's samples | V3 sample validation; the grounded-conflict rule | `spec_findings_confirmed` |
| Validity | Artifacts conform to schemas; exported OpenAPI is valid | Pydantic; openapi-spec-validator | `schema_valid_rate` |
| Traceability | Every claim resolves to evidence | Mandatory citations; manifest lineage | `citation_presence_rate` (must be 1.0) |
| Reproducibility | Same inputs produce the same outputs | Determinism test | `determinism` |
| Timeliness | We analyze the stated version of the document | SHA-256 pin; version recorded in the manifest | — |

## 2. Known input-data issues (observed before kickoff)

| ID | Observation | Effect | Handling |
|---|---|---|---|
| Q1 | CID TrueType fonts (MicrosoftYaHei, OpenSans) with Identity-H encoding; poppler warns about the Adobe-GB1 mapping | Possible character substitution | Grounding uses normalized text from the same extractor the verifier uses; T02 spike checks known rows |
| Q2 | Table descriptions wrap across lines (e.g. `user_email … Requirement: 1.22.16 or later`) | Multi-line rows | V2b applies to single-line rows only; wrapped rows get `V2_ROW_NOT_FOUND` (info) and are counted separately |
| Q3 | Typos inside the document (e.g. the sample value `"Fist Name"`) | Not defects of our tool | Transcribed faithfully; only contract violations become findings |
| Q4 | Sample value `"Interviemw"` violates the documented enum (pp. 52, 56, 63) | Genuine document defect | Expected `SPEC_SELF_INCONSISTENCY`, used as a known-positive test |
| Q5 | At least one request sample appeared not to parse as JSON (pre-event probe, unconfirmed) | Possible `SPEC_MALFORMED_SAMPLE` | Confirm in T13 before claiming |
| Q6 | Placeholders in samples: `{{host}}`, masked tokens, `example@*.com` | Must not be treated as real data | Excluded from format checks; not flagged |
| Q7 | Enums defined in chapter "Schemas" sections, apart from the endpoint tables | Cross-section references | `enum_citation` separate from the row citation; schema sections extracted first |
| Q8 | The community OpenAPI matches the PDF at endpoint level (107/107) | Community findings, if any, will be at field level and fewer | Report honestly; don't inflate |

## 3. Output-quality risk register

| Risk | Detector | Residual risk |
|---|---|---|
| Hallucinated field that exists nowhere in the document | V2_CITATION_NOT_FOUND | Low |
| Real quote, wrong interpretation (e.g. `required: true` for an `F` row) | V2_ROW_MISMATCH | Medium for wrapped rows (only name-grounded), so measured by audit |
| Missed field | V5_COVERAGE_GAP | Medium, because the row detector misses wrapped rows; the audit samples for misses |
| Wrong type normalization (e.g. `Array[Object]` → `object`) | V2b compares `type_raw`; normalization is a deterministic lookup table | Low |
| Sample copied with a "fix" | `V2_SAMPLE_NOT_VERBATIM` (every sample line must appear verbatim, in order, in the section text) + the skill rule "never repair" | Low |
| Spurious spec finding caused by an extraction error | Grounded-conflict rule + human confirmation before any claim | Low |

## 4. Bias assessment
Bias here means systematic error that pushes results in one direction. The relevant biases are cognitive, methodological and model-related, not demographic, because the system processes no personal data.

| # | Bias | How it could appear | Mitigation | How we check it |
|---|---|---|---|---|
| B1 | **Model prior / convention bias** | The LLM "corrects" the document toward common REST conventions: adds `id` fields, assumes camelCase, normalizes typos | Faithful-transcription skill; V2 grounding rejects anything not on the page | Audit item: "field exists verbatim on page" |
| B2 | **Anchoring bias** | Seeing the community OpenAPI would make the extractor copy its choices, turning the comparison circular | Blind extraction (R6); compare runs after contracts are frozen | Session exports show the community file was never opened during extraction |
| B3 | **Verification survivorship bias** | Reporting only what the verifier can check makes quality look higher than it is | Report `V2_ROW_NOT_FOUND` counts and UNCHECKABLE items explicitly; the audit samples from **all** items, not only verified ones | Metric: `row_check_applicability` |
| B4 | **Evaluator / self-assessment bias** | The builder audits their own tool and leans toward "correct" | **Blind audit:** the auditor sees the page and claimed item, not the verifier status; a stratified random sample with a fixed seed; Claude Code as an optional second auditor, with disagreements recorded | Inter-rater agreement if two auditors |
| B5 | **Selection bias** | One vendor's document has an unusually regular layout, so results won't generalize | Claims scoped to "this document class"; Stretch 2 runs on a second document | Limitations section in the report |
| B6 | **Layout bias** | Table fields verify better than prose rules (e.g. "Omit this parameter if…") | Per-location metrics (header, body, response, schema); prose rules marked out of scope | Metrics broken down by location |
| B7 | **Confirmation bias in findings** | Treating every candidate finding as real because it supports the pitch | Findings start as CANDIDATE; only human-confirmed findings are claimed | `findings_review.csv` |
| B8 | **Metric-gaming (reward hacking)** | The agent weakens tests or thresholds, or edits artifacts by hand | Protected paths + `make guard`; thresholds set before extraction and committed | Git history of `eval/thresholds.yaml` |
| B9 | **Language bias** | English-only document | Scope statement | — |

## 5. Blind audit protocol (summary; full version in EVALUATION_FRAMEWORK §4)
1. `specproof audit-sample --n 40 --seed 20260926` draws a stratified sample of 4 items per chapter across locations, **including quarantined and row-unchecked items**.
2. The sheet shows the page image reference, the claimed item and the citation. It hides verification status.
3. The auditor marks each item: correct / incorrect (with the reason) / missing-neighbor noticed.
4. Precision = correct ÷ audited, with a Wilson 95% interval, reported with *n*.

## 6. Limitations we will state publicly
- Validated on one vendor PDF with a regular table layout. Other layouts may need new row detectors.
- Prose-only rules (conditional requirements, version notes) are captured as descriptions, not verified semantics.
- Client conformance covers Python Pydantic models only.
- Hand-audit precision has the confidence interval of an *n* = 40 sample. We say so.
