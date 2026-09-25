---
name: specproof-extract
description: Extract a cited, verifiable API contract from a specification document section-by-section for SpecProof. Use when asked to extract, re-extract, or repair contract JSON for sections of an API spec PDF.
---

# SpecProof extraction skill

## Purpose
Transcribe API specification sections into contract JSON files. The deterministic verifier checks every item, so **faithful transcription with exact citations** is the only goal. Do not interpret generously, do not fill gaps, and do not fix the document.

## Inputs
- `artifacts/work/spec.pdf`: the source document (read pages directly with document understanding).
- `artifacts/sections_index.json`: authoritative list of sections, with `section_id`, `title`, `page_start`, `page_end`, `method_hint`, `path_hint`.
- Optional: `artifacts/feedback/<section_id>.md` when re-extracting.

## Section kinds
`sections_index.json` marks each section `kind: endpoint` or `kind: schema`. Schema sections (e.g. "3.1 Schemas", "4.1 Schemas") define shared objects and enums. Extract them first, one per chapter, to `artifacts/contract/<section_id>.json`, with `kind: schema` and a `definitions` list of FieldSpecs. Endpoint sections reference them through `enum_citation` and `schema_ref`.

## Procedure (per endpoint section)
1. Look up the section in `sections_index.json`. Read **only** pages `page_start..page_end`.
2. Record `method`, `path` and `permission_key` exactly as printed.
3. For each table (Request Header, Query/Path parameters, Request Body, Response Body), create one FieldSpec per row:
   - `name`: exactly as printed.
   - `required`: `true` for `T`, `false` for `F`, `null` if the table has no Required column.
   - `type`: normalized to one of `string, integer, number, boolean, object, array, unknown`. Record the printed type in `type_raw`.
   - `enum`: only if the document lists allowed values explicitly, either in this row or in the chapter's **Schemas** section (e.g. §4.1 defines `visit_reason: enum reason {Interview,Business,Cooperation,Others}` on page 52). Copy the values exactly, including any typos. When the enum comes from a Schemas section, set `enum_citation` to that page and quote, separately from the row citation.
   - `citation.quote`: a **verbatim** substring of the page text, 12–200 characters, that contains the field name. Prefer the table row, e.g. `first_name              T           String`. Whitespace may differ; characters may not.
   - `citation.page`: the 1-based PDF page where that quote appears.
4. Samples: copy the request sample body (the JSON inside `--data-raw '...'`) into `samples.request.raw`, character-for-character. Copy the response sample into `samples.response.raw`. Give each sample its own citation. **Do not repair malformed JSON**; the verifier records it as a spec defect. The verifier checks that every line of `raw` appears verbatim, in order, in the section text (`V2_SAMPLE_NOT_VERBATIM`), so any "cleanup" fails verification.
5. Write `artifacts/contract/<section_id>.json` following the schema in `docs/TECHNICAL_ARCHITECTURE.md` §5. Set `extraction.prompt_version` to `extract-v1`.
6. Run `specproof verify --section <section_id>` and report the printed status line verbatim.

## Parallelism
When asked to extract a whole chapter, delegate one subagent per chapter, or per ~8 sections for big chapters. Each subagent receives this skill, the chapter's section IDs, and the page range. It returns only the file paths it wrote and its verify status line.

## Re-extraction (loop)
Read `artifacts/feedback/<section_id>.md`. It lists reason codes with evidence. Fix **only** the listed items. Do not touch items that passed. Increment `extraction.attempt`.

## Never
- Never open third-party specs of this API (for example, the community OpenAPI) during extraction.
- Never paraphrase inside `quote`, change a sample, or "correct" an enum.
- Never mark anything as verified yourself.
- Never edit files outside `artifacts/contract/` and `artifacts/conformance/`.

## Worked example (User Registration, verified layout)
The document shows a Request Body row `first_name  T  String  First name of the user.`, which becomes:
```json
{"name": "first_name", "location": "body", "required": true, "type": "string", "type_raw": "String",
 "enum": null, "description": "First name of the user.",
 "citation": {"page": 14, "quote": "first_name              T           String"}}
```
(Verified: this row is on PDF page 14. Always read the actual page.)
