# T10: Client conformance on py-unifi-access (inventory, mapping, model diff, sample replay)

Est. 120 min · Modes: Plan → Agent (spike) → Agent (build) → Spec Auditor (mapping) → Agent (run) · Tests: CNF-001..013, CNF-R01
Pre-flight: `git rev-parse HEAD > .specproof_task_base && make check && ls artifacts/work/py-unifi-access`

## P: Plan mode
```text
Task T10. Read docs/TECHNICAL_ARCHITECTURE.md section 8, docs/TEST_PLAN.md CNF rows and
FX-04, docs/DATA_GOVERNANCE_AND_LINEAGE.md rules R4 and R7. Plan in at most 20 lines. No edits.
```

## A1: Agent mode (spike, 15 min, read-only)
```text
Read artifacts/work/py-unifi-access/unifi_access_api/client.py and models/*.py. Write
review/SPIKE_T10.md containing:
(1) how HTTP calls are made: the exact helper name(s) and the argument position of the
    method and the path, with 2 real code excerpts including file:line;
(2) how paths are built (constants, f-strings, concatenation);
(3) every Pydantic model class with file:line and whether it uses aliases or
    model_config options (extra, populate_by_name);
(4) the envelope handling: does the client unwrap {"code","msg","data"} before
    model_validate? Quote the code.
Do not modify any other file.
```

## A2: Agent mode (build)
```text
ROLE
Lead engineer on SpecProof. AGENTS.md is binding. Test-first.

TASK
T10: implement client conformance checking, informed by review/SPIKE_T10.md.

DELIVERABLES
1. conformance/inventory.py: scan_endpoints(pkg_dir) -> list[EndpointRef(path_norm,
   method, file, line, dynamic: bool)]
   - Walk every .py file with ast. Collect Constant str values and JoinedStr (f-strings)
     containing "/api/v1/developer/". Render FormattedValue parts as "{}", then
     normalize_path.
   - Method: if the literal is an argument of a Call whose func is an Attribute named
     get/post/put/patch/delete, use that. Otherwise, if the Call's first positional arg is
     a str Constant in {GET,POST,PUT,PATCH,DELETE}, use that (the pattern from
     SPIKE_T10). Else "UNKNOWN".
   - Paths built dynamically (BinOp or str.join with non-constants) -> dynamic=True
     (UNCHECKABLE).
2. conformance/check.py: compare the inventory with verified contracts:
   documented -> ok; path known but method differs -> CLIENT_METHOD_MISMATCH;
   path unknown -> CLIENT_UNDOCUMENTED_ENDPOINT; dynamic -> recorded as UNCHECKABLE
   (not a finding). Code evidence = file:line + a snippet of the line.
3. conformance/mapping.py: load artifacts/conformance/mapping.yaml, a list of
   {section_id, model (dotted path), json_path ("data" | "data[*]"), code: {file, line}}.
   Validate that the file exists and that the line contains f"class {ModelName}".
   Otherwise reject the entry with a clear error (CNF-007). Only VERIFIED* sections allowed.
4. conformance/models.py: diff_model(model_cls, section) -> list[Finding], using
   model_fields: key = alias or name; required = field.is_required();
   annotation mapped to FieldType (str->string, int->integer, float->number, bool->boolean,
   list->array, BaseModel/dict->object, Optional[X]->X, Literal[str...]->string with enum).
   - Model-required key absent from the doc response fields ->
     CLIENT_REQUIRES_UNDOCUMENTED_FIELD
   - Type differs from the doc -> CLIENT_TYPE_MISMATCH
   Evidence: code (file:line of the class) plus the doc citation of the field where one
   exists.
5. conformance/replay.py
   - generate(mappings, contracts) -> Python source for
     artifacts/conformance/test_sample_replay.py: one pytest function per mapping, named
     test_replay_<section_id>_<Model>. It embeds the doc response sample JSON (from the
     contract, via json.loads of a string literal), extracts json_path, and calls
     Model.model_validate(item) on each item. Deterministic ordering. py_compile-clean.
   - run(client_dir) -> results: create an isolated venv in artifacts/work/replay-venv,
     pip install the client at its pinned checkout (-e artifacts/work/py-unifi-access) plus
     pytest, and run the generated file with --junitxml. Parse the results.
     A failed test -> CLIENT_SAMPLE_REJECTED (the Pydantic error message, doc citation of
     the sample, code evidence of the model). A collection or import error ->
     environment_error recorded in artifacts/findings/conformance.json under "errors",
     NOT as findings (CNF-013).
6. CLI conform --client PATH: runs inventory + check + mapping + model diff + replay.
   Writes artifacts/findings/conformance.json and the generated test file; appends manifest
   records.
7. Fixture FX-04 tests/fixtures/mini_client/ exactly as in TEST_PLAN.

TESTS FIRST
tests/integration/test_conformance.py: CNF-001..013 (for CNF-012 the replay may run in
the current interpreter for the mini client; the isolated venv is only for real runs).
tests/e2e/test_real_source.py: CNF-R01 (11 distinct /api/v1/developer/ paths).

CONSTRAINTS
Third-party code is imported ONLY inside the replay venv; never import the real client
into the specproof process. Do not modify verify/ or contracts.

ACCEPTANCE CRITERIA
make check green (final 5 lines); CNF-R01 passes; inventory table for the real client
printed.

OUTPUT
SESSION SUMMARY.
```

## M: Spec Auditor mode (create the mapping; Bob reads code + contracts)
```bash
touch .specproof_extraction_task   # guard on: mapping is an AI artifact
```
```text
ROLE
Spec Auditor for SpecProof. You map client models to contract sections. You never judge
conformance yourself.

TASK
Create artifacts/conformance/mapping.yaml for artifacts/work/py-unifi-access.

STEPS
1. Read review/SPIKE_T10.md, then the client's models/*.py and the methods in client.py
   that return those models.
2. For each model, find the endpoint whose RESPONSE it parses, by reading the client
   method that calls the endpoint and constructs the model.
3. Only map sections whose status in artifacts/status.json is VERIFIED or
   VERIFIED_WITH_SPEC_FINDINGS.
4. For each mapping, write:
   - section_id: S-x.y
     model: unifi_access_api.models.<module>.<Class>
     json_path: "data" or "data[*]" (per the envelope handling in SPIKE_T10)
     code: {file: <path relative to the client repo>, line: <line of "class <Class>">}
     evidence: "<one line quoting the client method that links endpoint and model, with file:line>"
5. If a model cannot be linked to an endpoint with evidence, do NOT map it. List it at the
   end of your reply as "unmapped: <Class> - reason".
6. Run: specproof conform --client artifacts/work/py-unifi-access, then specproof guard.

OUTPUT
The mapping file content, the unmapped list, and the conform and guard outputs verbatim.
SESSION SUMMARY.
```
```bash
rm .specproof_extraction_task
```

## V: Ask mode
```text
Print artifacts/findings/conformance.json summarized as: counts by finding type, the list
of UNCHECKABLE inventory entries, any "errors", and every CLIENT_SAMPLE_REJECTED finding with
its full Pydantic message and both citations. Verbatim values only.
```

## Human check (before T13 confirmation)
Run the generated test yourself: `artifacts/work/replay-venv/bin/pytest artifacts/conformance/test_sample_replay.py -v`. A finding is only real if you can reproduce it.
