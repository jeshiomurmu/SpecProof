# Changelog

- T00: Planning kit committed before kickoff (docs, Bob config, source pins, thresholds). No product code.
- T01: Scaffolded package, Typer CLI stubs for all 14 commands, Makefile, ruff/mypy/pytest config, pre-commit (ruff, gitleaks, mypy), CI, LICENSE; tests CLI-001, GOV-005.
- T02: Added text/hash/JSON utilities, pinned-source fetch, pdfplumber page ingest with cache and manifest lineage, FX-01 synthetic PDF; pdfplumber chosen as default after the spike showed pdftotext misaligns table rows.
- T03: Added deterministic segmenter and `specproof segment`; real PDF gives 131 sections (108 endpoint = 107 API + 1 inbound webhook callback, 15 overview, 8 schema), see review/SEG_NOTES.md.
- T04: Added Pydantic v2 contract, verification, finding and manifest models; exported docs/schemas/contract.schema.json.
- T05: Added the deterministic verification engine (V1-V5) and `specproof verify`, FX-02 golden contracts, FX-03 mutation matrix; fixed page extraction to keep table column gaps (x_density=3) after a real-PDF check.
- T06: Added the classification state machine with grounded spec findings, retry feedback files, `classify`, `loop-status` and the protected-path `guard`.
- T09: Added OpenAPI 3.1 export of verified sections (with PDF citations as x- extensions) and the field-level community comparison; real-data run pending extraction (T07-T08).
- T10: Added client conformance: AST endpoint inventory (constants, helpers, local variables), method/undocumented checks, mapping validation, model diff and sample replay in a separate interpreter; real client inventory finds 11 developer paths (F10).
- T11: Added metrics with explicit denominators and truncation, the eval gate against eval/thresholds.yaml, and blind-audit sampling and scoring.
- T12: Added the self-contained HTML evidence pack, SARIF export, findings.json, landing page, `make site`, contract/mapping lineage records, and end-to-end tests (synthetic pipeline, determinism, performance; real-source tests skip until extraction).
- T07: IBM Bob extracted the pilot contracts S-3.2, S-4.1 and S-4.2.
- T08: IBM Bob extracted chapter 4 attempt 1; Claude Code extracted the remaining 104 sections and all retries after the Bob allowance ran out, and fixed verifier gaps found on real samples.
- T10: Added the client model mapping (6 models) and ran conformance with replay under Python 3.14.
- T12: Ran the full pipeline on the real specification: 115/116 sections verified, 1 quarantined (S-4.4).
- T14: Added make readme (results table from metrics.json), the Pages workflow, and an honest attribution section in the README.
