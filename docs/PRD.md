# PRD: SpecProof

| | |
|---|---|
| Status | Approved for hackathon build (IBM Bob 2.0 Hackathon, Sep 25–27, 2026) |
| Owner | Jeshio (solo) |
| Workflow targeted | **Application maintenance + testing** of integrations governed by document-only specifications |

## 1. Problem statement
When an API or data standard is specified only as a document (PDF, DOCX, XLSX), developers must transcribe it into code by hand. This causes three recurring failures:

1. **Transcription errors.** Wrong required flags, wrong types and missed enum values reach production.
2. **Document defects propagate.** When the spec contradicts itself (e.g. a sample that violates its own enum), developers copy the defect.
3. **No verification is possible.** Machine-readable tooling (OpenAPI diff, contract testing) needs a machine-readable spec that does not exist. Hand conversions carry disclaimers instead of guarantees.

**Evidence (verified, see `VERIFIED_FACTS.md`):**
- The UniFi Access API ships only as a 194-page PDF.
- The community OpenAPI conversion warns it may contain omissions or errors.
- The PDF contradicts itself: `visit_reason` enum vs. the sample value `"Interviemw"`, found on pages 52, 56 and 63.

## 2. Target users

| Persona | Job to be done | Today's pain |
|---|---|---|
| **Integration engineer** (primary) | "Give me a contract I can trust for this PDF spec, and tell me what in my code violates it." | Days of manual reading; errors surface in production |
| **Client-library maintainer** | "Prove my models match the vendor's documented payloads." | No test oracle exists |
| **QA / platform lead** | "Give me evidence of conformance I can show an auditor or partner." | Evidence is screenshots and tribal knowledge |

## 3. Goals and non-goals

**Goals**
- G1: Produce a structured contract from a document-only spec, **with a page citation for every item**.
- G2: Verify every item deterministically, and self-correct extraction errors in a bounded loop.
- G3: Separate *extraction errors* from *defects in the document itself*, and report the latter as findings.
- G4: Check a real client codebase against the verified contract, including replaying the document's own samples through the client's models.
- G5: Produce a self-contained evidence pack (HTML + JSON + SARIF) with full lineage.

**Non-goals (hackathon scope)**
- Calling live APIs, or any network traffic beyond fetching pinned sources.
- Scanned or OCR-only documents (the target PDF has a text layer).
- Languages other than Python for conformance.
- Auto-merging fixes into third-party repos. We produce issues or patches for humans.

## 4. Scope

| MVP (must ship) | Stretch 1 | Stretch 2 |
|---|---|---|
| Ingest, segment, extract (Bob), verify V1–V5, loop, classify, community compare, conformance on `py-unifi-access`, report, eval gate, static demo site | Version diff between two PDF versions (only if an older version is found, U6) | Generalization run on a second document-only spec (e.g. an XLSX data dictionary) |

## 5. User stories and acceptance criteria

| ID | Story | Acceptance criteria |
|---|---|---|
| US-01 | As an integration engineer, I point SpecProof at a spec PDF and get a list of every endpoint section. | `specproof segment` produces `sections_index.json` with ≥ 107 endpoint sections for the UniFi PDF; each has title, page range, method hint, path hint |
| US-02 | I get a contract where every field shows where it came from. | 100% of contract items carry `{page, quote}`; `quote` is 12–200 chars |
| US-03 | I trust that citations are real. | Verifier rejects any quote not found on its cited page (V2), demonstrated by test VER-004 |
| US-04 | I trust that required flags and types were read correctly. | Verifier checks each table field against its row line (V2b); mismatches get reason code `V2_ROW_MISMATCH` |
| US-05 | Extraction errors are fixed automatically where possible. | Failed sections get `feedback/<id>.md` with reason codes and evidence; loop re-extracts at most 2 times; first-pass vs final verified rates are reported |
| US-06 | I learn where the **document itself** is wrong. | When a sample conflicts with a grounded contract item and both are grounded, a `SPEC_SELF_INCONSISTENCY` finding is emitted with both citations (F7 reproduced) |
| US-07 | I see how an existing hand conversion differs from the document. | `specproof compare --community` lists discrepancies, each adjudicated with a PDF citation |
| US-08 | I learn whether my client code conforms. | `specproof conform` reports endpoint inventory verdicts and model-field diffs, and generates runnable pytest tests replaying doc response samples through client models |
| US-09 | I can hand the result to someone else. | `artifacts/report/index.html` is self-contained (no external requests), links every finding to its evidence, and shows methodology and limitations |
| US-10 | I can reproduce everything. | Fresh clone + `make setup fetch pipeline` reproduces byte-identical committed artifacts (determinism = 1.0) |

## 6. Functional requirements

| ID | Requirement |
|---|---|
| FR-01 | Fetch pinned sources and verify SHA-256; refuse to run on hash mismatch |
| FR-02 | Extract per-page text with layout preserved; record extractor name and version in the manifest |
| FR-03 | Deterministically segment the document into `endpoint` and `schema` sections |
| FR-04 | Contract schema per `TECHNICAL_ARCHITECTURE.md` §5, validated with Pydantic |
| FR-05 | Verification rules V1–V5 with the exact reason codes in §6 of the architecture doc |
| FR-06 | Bounded loop: at most 2 re-extractions per section; feedback files are machine-generated |
| FR-07 | Classification state machine (§7 of the architecture doc) with final statuses VERIFIED, VERIFIED_WITH_SPEC_FINDINGS, QUARANTINED |
| FR-08 | Export verified contract to OpenAPI 3.1; validate the export with an OpenAPI validator |
| FR-09 | Community comparison with path normalization (leading slash, parameter names) |
| FR-10 | Client conformance: endpoint inventory, model field diff, sample replay test generation |
| FR-11 | Report generation: HTML (self-contained), `findings.json`, `findings.sarif`, `metrics.json` |
| FR-12 | Eval gate against `eval/thresholds.yaml`; non-zero exit on failure |
| FR-13 | Manifest lineage for every artifact (inputs, hashes, producer, version) |

## 7. Non-functional requirements

| ID | Requirement |
|---|---|
| NFR-01 Determinism | Identical inputs produce byte-identical outputs |
| NFR-02 Offline | All stages except `fetch` run without network |
| NFR-03 Performance | Deterministic stages on the 194-page PDF finish in < 60 s on a laptop |
| NFR-04 Traceability | Every finding resolves to page + quote and/or file + line |
| NFR-05 Safety | No credentials, no live API calls, no third-party full text committed |
| NFR-06 Quality | `make check` green; ≥ 85% coverage; `mypy --strict` on `src/` |
| NFR-07 Portability | macOS, Linux and Windows (pure-Python PDF stack; `pdftotext` optional fallback) |

## 8. Hackathon requirement traceability

| Brief clause | How SpecProof satisfies it | Evidence judges can check |
|---|---|---|
| "Improves a specific developer workflow" (application maintenance, testing) | Maintaining integrations against document-only specs | README problem section, demo |
| "Clearly defining a problem where time, effort, or errors are too high" | Manual transcription; propagating document defects; no verification possible | F1, F7, manual baseline timing (EVALUATION §5) |
| "Using IBM Bob 2.0, build a working prototype on a real or sample project" | Real PDF, real community spec, real client library | Live demo URL, repo, `make pipeline` |
| "Leverage Agent mode" | All engine tasks built test-first in Agent mode | `bob_sessions/INDEX.md` |
| "Parallel tasks" | Chapter extraction runs concurrently | T08 session export |
| "Subagents" | One subagent per chapter, clean context, JSON-only returns | T08 session export |
| "Document understanding" | Bob reads the PDF directly; it is the product's input | T07/T08 exports |
| "Manage and improve multiple steps, not just assist with coding" | Extract → verify → feedback → re-extract → classify → compare → conform → report | LOOP_ENGINEERING.md, report loop stats |
| "Clearly demonstrate impact" | Minutes per endpoint vs manual baseline; confirmed findings; first-pass vs post-loop accuracy | EVALUATION_FRAMEWORK.md, `metrics.json` |
| Submission: files where Bob assisted + session summary screenshots | `bob_sessions/` curated with INDEX | Repo |

## 9. Success metrics
Defined in `EVALUATION_FRAMEWORK.md`. Headline metrics: endpoint coverage, citation grounding rate, final verified rate, audited precision, confirmed spec defects, confirmed client issues, minutes per verified endpoint vs manual baseline.

## 10. Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Bobcoins run out mid-extraction | Medium | High | Pilot on 2 sections first; chapter batching; cache; never re-extract VERIFIED |
| Bob page references drift on a 194-page PDF | Medium | Medium | The deterministic segmenter gives each subagent exact page ranges; V2 catches wrong pages |
| Layout text breaks a table row across lines | Medium | Medium | V2b is scoped to single-line rows; multi-line rows fall back to name-only grounding and are counted separately |
| Few real client findings | Medium | Medium | Sample replay produces facts either way; report honestly; the spec-defect findings (F7) already exist |
| Overclaiming in the pitch | Low | High | Numbers come only from `metrics.json`; blind audit; limitations section |

## 11. Release criteria (demo-ready)
- [ ] `make check`, `make eval` and `make guard` are green on a fresh clone.
- [ ] Report deployed at a public URL. Opens in < 2 s; no external requests.
- [ ] README results table generated from `metrics.json`.
- [ ] At least one confirmed spec defect and every confirmed client finding hand-verified against the PDF.
- [ ] `bob_sessions/` complete, with INDEX, exports and screenshots for every task.
- [ ] Video ≤ 5 min, slides PDF, cover image, submission fields done by Sun 18:00 BST.
