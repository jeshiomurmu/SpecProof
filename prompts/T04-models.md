# T04: Data models

Est. 45 min · Modes: Plan → Agent · Tests: MOD-001..008
Pre-flight: `git rev-parse HEAD > .specproof_task_base && make check`

## P: Plan mode
```text
Task T04. Read docs/TECHNICAL_ARCHITECTURE.md section 5 in full (5.1-5.6 and the finding type
list) and docs/TEST_PLAN.md MOD rows. List every model, field and validator you will
implement, in at most 20 lines. No edits.
```

## A: Agent mode
```text
ROLE
Lead engineer on SpecProof. AGENTS.md is binding. Test-first.

TASK
T04: implement the Pydantic v2 data models that every later stage depends on. Field names and
vocabularies must match docs/TECHNICAL_ARCHITECTURE.md section 5 EXACTLY; other tasks and the
extraction skill rely on them.

DELIVERABLES
1. src/specproof/models/contract.py
   - Citation: page: int (>= 1); quote: str. A validator requires 12 <= len(norm(quote)) <= 200.
   - FieldType = Literal["string","integer","number","boolean","object","array","unknown"]
   - Location = Literal["header","path","query","body","response"]
   - FieldSpec: name, location, required: bool | None, type: FieldType, type_raw: str,
     enum: list[str] | None, enum_citation: Citation | None, description: str | None,
     example: str | int | float | bool | None, min_version: str | None,
     schema_ref: str | None, citation: Citation
   - Sample: raw: str, citation: Citation
   - Samples: request: Sample | None, response: Sample | None
   - Extraction: producer: str, mode: str, prompt_version: str, attempt: int (>= 1),
     bob_task_ref: str | None
   - ContractSection: schema_version: Literal[1]; section_id matching r"^S-\d{1,2}\.\d{1,2}$";
     kind: Literal["endpoint","schema","overview"]; title; method; path; permission_key;
     citations: dict[str, Citation]; fields: list[FieldSpec]; definitions: list[FieldSpec];
     samples: Samples; extraction: Extraction.
     Validators: an endpoint requires method (GET|POST|PUT|PATCH|DELETE) and path; a schema
     forbids method and path.
     classmethod load(path) -> ContractSection: gives a clear error on schema_version mismatch.
     Method dump(path) uses io_json.dump_json with lists sorted by (location, name).
   - model_config = ConfigDict(extra="forbid") on all models.
2. src/specproof/models/verification.py
   - IssueCode: Literal[...] of EVERY code in architecture section 6, including
     V2_SAMPLE_NOT_VERBATIM.
   - Issue: code, severity ("error"|"warning"|"info"), category
     ("extraction"|"sample_conflict"|"info"), field: str | None, message,
     evidence: Citation | None, hint: dict[str, str | int] | None
   - VerificationResult: section_id, attempt, issues (sorted), counts: dict[str, int]
   - SectionStatus = Literal["EXTRACTED","NEEDS_RETRY","VERIFIED",
     "VERIFIED_WITH_SPEC_FINDINGS","QUARANTINED"]
3. src/specproof/models/findings.py
   - Evidence: kind ("doc"|"code"), page, quote, file, line, snippet (all optional except kind)
   - FindingType: Literal of every type listed in architecture section 5.6
   - Finding: id, type, severity ("high"|"medium"|"low"|"info"), section_id, title,
     evidence: list[Evidence], review: {status: "CANDIDATE"|"CONFIRMED"|"REJECTED",
     reviewer, note}
   - staticmethod make_id(type, section_id, field, evidence) ->
     "F-" + sha256("|".join([type, section_id, field or ""] + sorted(canonical evidence
     strings)))[:8]
4. Complete src/specproof/models/manifest.py (Producer model; typed inputs).
5. Export ContractSection.model_json_schema() to docs/schemas/contract.schema.json (sorted keys).

TESTS FIRST
tests/unit/test_models.py implementing MOD-001..008 exactly as in docs/TEST_PLAN.md.

CONSTRAINTS
No I/O except load/dump helpers. mypy --strict with the pydantic plugin.

ACCEPTANCE CRITERIA
make check green; docs/schemas/contract.schema.json exists; paste the final 5 lines of
make check.

OUTPUT
SESSION SUMMARY.
```
