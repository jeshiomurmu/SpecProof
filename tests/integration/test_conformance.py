import py_compile
import shutil
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
import yaml
from typer.testing import CliRunner

from specproof.cli import app
from specproof.conformance.check import check_inventory
from specproof.conformance.inventory import EndpointRef, scan_endpoints
from specproof.conformance.mapping import Mapping, MappingError, validate_mapping
from specproof.conformance.models import ModelField, describe_model, diff_model
from specproof.conformance.replay import generate, run_replay
from specproof.ingest.segment import Section
from specproof.models.contract import ContractSection
from specproof.util.io_json import load_json

Good = Callable[[str], dict[str, Any]]
FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"
MINI = FIXTURES / "mini_client"
REPO_SRC = Path(__file__).resolve().parents[2] / "src"


@pytest.fixture(scope="module")
def inventory() -> list[EndpointRef]:
    return scan_endpoints(MINI)


def _one(refs: list[EndpointRef], path: str) -> EndpointRef:
    [ref] = [r for r in refs if r.path_norm == path]
    return ref


def _mapping(model: str = "models.Widget", file: str = "models.py") -> Mapping:
    return Mapping(section_id="S-2.3", model=model, json_path="data", file=file, line=7)


def _index(sections: dict[str, Section]) -> list[dict[str, Any]]:
    return [s.entry for s in sections.values()]


@pytest.mark.integration
def test_CNF_001_constant_path_with_method(inventory: list[EndpointRef]) -> None:
    ref = _one(inventory, "/api/v1/widgets")
    assert (ref.method, ref.file, ref.dynamic) == ("POST", "client.py", False)


@pytest.mark.integration
def test_CNF_002_fstring_path_normalized(inventory: list[EndpointRef]) -> None:
    assert _one(inventory, "/api/v1/widgets/{}").method == "GET"


@pytest.mark.integration
def test_CNF_003_method_via_attribute(inventory: list[EndpointRef]) -> None:
    ref = _one(inventory, "/api/v1/gadgets")
    assert ref.method == "GET"
    assert "session.get" in ref.snippet


@pytest.mark.integration
def test_CNF_004_method_via_helper_argument(inventory: list[EndpointRef]) -> None:
    ref = _one(inventory, "/api/v1/widgets/{}")
    assert ref.method == "GET" and '_request("GET"' in ref.snippet


@pytest.mark.integration
def test_CNF_005_undocumented_endpoint(
    inventory: list[EndpointRef], synthetic_sections: dict[str, Section]
) -> None:
    findings, _ = check_inventory(inventory, _index(synthetic_sections), [], "mini_client")
    assert [(f.type, f.title) for f in findings] == [
        (
            "CLIENT_UNDOCUMENTED_ENDPOINT",
            "Client calls GET /api/v1/gadgets, which the specification does not document.",
        )
    ]
    [code] = findings[0].evidence
    assert (code.kind, code.file, code.line) == ("code", "mini_client/client.py", 20)


@pytest.mark.integration
def test_CNF_006_dynamic_path_is_uncheckable(
    inventory: list[EndpointRef], synthetic_sections: dict[str, Section]
) -> None:
    dynamic = [r for r in inventory if r.dynamic]
    assert [(r.method, r.line) for r in dynamic] == [("DELETE", 23)]
    findings, uncheckable = check_inventory(inventory, _index(synthetic_sections), [], "mc")
    assert all(f.evidence[0].line != 23 for f in findings)
    assert [u["line"] for u in uncheckable] == [23]


@pytest.mark.integration
def test_CNF_006b_method_mismatch(synthetic_sections: dict[str, Section], good: Good) -> None:
    ref = EndpointRef("/api/v1/widgets/{}", "PUT", "client.py", 9, False, "x")
    contract = ContractSection.model_validate(good("S-2.3"))
    findings, _ = check_inventory([ref], _index(synthetic_sections), [contract], "mc")
    assert [f.type for f in findings] == ["CLIENT_METHOD_MISMATCH"]
    assert [e.page for e in findings[0].evidence if e.kind == "doc"] == [6]


@pytest.mark.integration
def test_CNF_007_mapping_citation_check() -> None:
    assert validate_mapping(_mapping(), MINI, {"S-2.3"}) == _mapping()
    with pytest.raises(MappingError, match=r"line 6 of models\.py does not contain 'class Widget'"):
        validate_mapping(Mapping("S-2.3", "models.Widget", "data", "models.py", 6), MINI, {"S-2.3"})
    with pytest.raises(MappingError, match="not VERIFIED"):
        validate_mapping(_mapping(), MINI, {"S-2.2"})
    with pytest.raises(MappingError, match="does not exist"):
        validate_mapping(_mapping(file="nope.py"), MINI, {"S-2.3"})


@pytest.mark.integration
def test_CNF_008_introspection() -> None:
    sys.path.insert(0, str(MINI))
    try:
        import models  # type: ignore[import-not-found]
    finally:
        sys.path.remove(str(MINI))
    fields = {f.key: f for f in describe_model(models.Widget)}
    assert fields["size"] == ModelField("size", True, "integer", None)
    assert fields["created_at"] == ModelField("created_at", True, "string", None)
    assert set(fields) == {"id", "name", "color", "size", "created_at", "serial"}


def _widget_fields() -> list[ModelField]:
    return [
        ModelField("id", True, "string", None),
        ModelField("name", True, "string", None),
        ModelField("color", True, "string", None),
        ModelField("size", True, "integer", None),
        ModelField("created_at", True, "string", None),
        ModelField("serial", True, "string", None),
    ]


@pytest.mark.integration
def test_CNF_009_requires_undocumented_field(good: Good) -> None:
    contract = ContractSection.model_validate(good("S-2.3"))
    findings = diff_model(_widget_fields(), _mapping(), contract, "mc")
    [undocumented] = [f for f in findings if f.type == "CLIENT_REQUIRES_UNDOCUMENTED_FIELD"]
    assert "`serial`" in undocumented.title
    assert [(e.kind, e.file, e.line) for e in undocumented.evidence] == [
        ("code", "mc/models.py", 7)
    ]


@pytest.mark.integration
def test_CNF_010_type_mismatch(good: Good) -> None:
    contract = ContractSection.model_validate(good("S-2.3"))
    findings = diff_model(_widget_fields(), _mapping(), contract, "mc")
    [mismatch] = [f for f in findings if f.type == "CLIENT_TYPE_MISMATCH"]
    assert "`created_at`" in mismatch.title and "integer" in mismatch.title
    assert sorted(e.kind for e in mismatch.evidence) == ["code", "doc"]
    assert [e.page for e in mismatch.evidence if e.kind == "doc"] == [6]


@pytest.mark.integration
def test_CNF_011_replay_generation(good: Good, tmp_path: Path) -> None:
    contract = ContractSection.model_validate(good("S-2.3"))
    source = generate([_mapping()], {"S-2.3": contract})
    assert source == generate([_mapping()], {"S-2.3": contract})
    assert source.count("def test_replay_") == 1
    assert "def test_replay_S_2_3_Widget()" in source
    target = tmp_path / "test_sample_replay.py"
    target.write_text(source, encoding="utf-8")
    py_compile.compile(str(target), doraise=True)


@pytest.mark.integration
def test_CNF_012_replay_finding(good: Good, tmp_path: Path) -> None:
    contract = ContractSection.model_validate(good("S-2.3"))
    target = tmp_path / "test_sample_replay.py"
    target.write_text(generate([_mapping()], {"S-2.3": contract}), encoding="utf-8")
    findings, errors = run_replay(
        target, [_mapping()], {"S-2.3": contract}, sys.executable, [MINI], "mc"
    )
    assert errors == []
    [finding] = findings
    assert finding.type == "CLIENT_SAMPLE_REJECTED"
    doc = [e for e in finding.evidence if e.kind == "doc"]
    code = [e for e in finding.evidence if e.kind == "code"]
    assert [e.page for e in doc] == [6]
    assert (code[0].file, code[0].line) == ("mc/models.py", 7)
    assert code[0].snippet is not None and "size" in code[0].snippet


@pytest.mark.integration
def test_CNF_013_import_error_is_environment_error(good: Good, tmp_path: Path) -> None:
    contract = ContractSection.model_validate(good("S-2.3"))
    broken = _mapping(model="broken_models.Widget", file="broken_models.py")
    target = tmp_path / "test_sample_replay.py"
    target.write_text(generate([broken], {"S-2.3": contract}), encoding="utf-8")
    findings, errors = run_replay(
        target, [broken], {"S-2.3": contract}, sys.executable, [MINI], "mc"
    )
    assert findings == []
    assert len(errors) == 1 and "not_a_real_dependency" in errors[0]["message"]
    assert errors[0]["kind"] == "environment_error"


@pytest.mark.integration
def test_CNF_015_mapping_file_with_producer(tmp_path: Path) -> None:
    from specproof.conformance.mapping import load_mappings, mapping_producer

    path = tmp_path / "mapping.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "producer": "claude-code",
                "entries": [
                    {
                        "section_id": "S-2.3",
                        "model": "models.Widget",
                        "json_path": "data",
                        "code": {"file": "models.py", "line": 7},
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    valid, errors = load_mappings(path, MINI, {"S-2.3"})
    assert (len(valid), errors) == (1, [])
    assert mapping_producer(path) == "claude-code"
    legacy = tmp_path / "legacy.yaml"
    legacy.write_text(yaml.safe_dump([]), encoding="utf-8")
    assert mapping_producer(legacy) == "unknown"


@pytest.mark.integration
def test_CNF_014_conform_cli(workspace: Path) -> None:
    shutil.copytree(FIXTURES / "contracts_good", workspace / "artifacts" / "contract")
    client = workspace / "client"
    shutil.copytree(MINI, client)
    runner = CliRunner()
    runner.invoke(app, ["verify", "--report-only"])
    runner.invoke(app, ["classify"])
    mapping = [
        {
            "section_id": "S-2.3",
            "model": "models.Widget",
            "json_path": "data",
            "code": {"file": "models.py", "line": 7},
        },
        {
            "section_id": "S-2.3",
            "model": "models.Widget",
            "json_path": "data",
            "code": {"file": "models.py", "line": 3},
        },
    ]
    (workspace / "artifacts" / "conformance").mkdir(parents=True)
    (workspace / "artifacts" / "conformance" / "mapping.yaml").write_text(yaml.safe_dump(mapping))
    result = runner.invoke(app, ["conform", "--client", str(client), "--python", sys.executable])
    assert result.exit_code == 0, result.output
    out = load_json(workspace / "artifacts" / "findings" / "conformance.json")
    types = sorted(f["type"] for f in out["findings"])
    assert types == [
        "CLIENT_REQUIRES_UNDOCUMENTED_FIELD",
        "CLIENT_SAMPLE_REJECTED",
        "CLIENT_TYPE_MISMATCH",
        "CLIENT_UNDOCUMENTED_ENDPOINT",
    ]
    assert len(out["mapping_errors"]) == 1 and "line 3" in out["mapping_errors"][0]
    assert [u["method"] for u in out["uncheckable"]] == ["DELETE"]
    assert (workspace / "artifacts" / "conformance" / "test_sample_replay.py").exists()
