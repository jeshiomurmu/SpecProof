import re
from pathlib import Path
from typing import Any, get_args

import pytest
from pydantic import ValidationError

from specproof.models.contract import Citation, ContractSection, FieldSpec
from specproof.models.findings import Evidence, Finding, FindingType
from specproof.models.verification import IssueCode

ALLOWED_TYPES = ["string", "integer", "number", "boolean", "object", "array", "unknown"]


def _citation(page: int = 4, quote: str = "name   T   String") -> dict[str, Any]:
    return {"page": page, "quote": quote}


def _field(**overrides: Any) -> dict[str, Any]:
    field: dict[str, Any] = {
        "name": "name",
        "location": "body",
        "required": True,
        "type": "string",
        "type_raw": "String",
        "enum": None,
        "enum_citation": None,
        "description": "Name of the widget.",
        "example": "Bolt",
        "min_version": None,
        "schema_ref": None,
        "citation": _citation(),
    }
    field.update(overrides)
    return field


def _section(**overrides: Any) -> dict[str, Any]:
    section: dict[str, Any] = {
        "schema_version": 1,
        "section_id": "S-2.2",
        "kind": "endpoint",
        "title": "Create Widget",
        "method": "POST",
        "path": "/api/v1/widgets",
        "permission_key": "edit:widget",
        "citations": {"path": _citation(quote="Request URL: /api/v1/widgets")},
        "fields": [
            _field(name="size", required=False, type="integer", type_raw="Integer"),
            _field(),
        ],
        "definitions": [],
        "samples": {"request": None, "response": None},
        "extraction": {
            "producer": "ibm-bob",
            "mode": "spec-auditor",
            "prompt_version": "extract-v1",
            "attempt": 1,
            "bob_task_ref": "T07",
        },
    }
    section.update(overrides)
    return section


def _doc_table_codes(repo_root: Path, heading: str, pattern: str) -> set[str]:
    text = (repo_root / "docs" / "TECHNICAL_ARCHITECTURE.md").read_text(encoding="utf-8")
    start = text.index(heading)
    end = text.index("\n## ", start + 1)
    return set(re.findall(pattern, text[start:end]))


@pytest.mark.unit
def test_MOD_001_quote_min_length() -> None:
    with pytest.raises(ValidationError):
        Citation(page=1, quote="12345678901")
    with pytest.raises(ValidationError):
        Citation(page=1, quote="   12345678901   ")
    assert Citation(page=1, quote="123456789012").quote == "123456789012"


@pytest.mark.unit
def test_MOD_002_quote_max_length() -> None:
    with pytest.raises(ValidationError):
        Citation(page=1, quote="x" * 201)
    Citation(page=1, quote="x" * 200)


@pytest.mark.unit
def test_MOD_003_page_at_least_1() -> None:
    with pytest.raises(ValidationError):
        Citation(page=0, quote="a long enough quote")


@pytest.mark.unit
def test_MOD_004_type_vocabulary() -> None:
    with pytest.raises(ValidationError):
        FieldSpec.model_validate(_field(type="str"))
    for allowed in ALLOWED_TYPES:
        assert FieldSpec.model_validate(_field(type=allowed)).type == allowed


@pytest.mark.unit
@pytest.mark.parametrize(
    "overrides",
    [
        {"method": None},
        {"path": None},
        {"method": "FETCH"},
        {"kind": "schema"},
        {"kind": "schema", "method": None},
    ],
    ids=["endpoint-no-method", "endpoint-no-path", "bad-method", "schema-method", "schema-path"],
)
def test_MOD_005_kind_constraints(overrides: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        ContractSection.model_validate(_section(**overrides))


@pytest.mark.unit
def test_MOD_005_valid_schema_section() -> None:
    schema = ContractSection.model_validate(
        _section(kind="schema", method=None, path=None, fields=[], definitions=[_field()])
    )
    assert schema.kind == "schema"


@pytest.mark.unit
def test_MOD_006_schema_version_rejected(tmp_path: Path) -> None:
    path = tmp_path / "S-2.2.json"
    ContractSection.model_validate(_section()).dump(path)
    path.write_text(
        path.read_text(encoding="utf-8").replace('"schema_version": 1', '"schema_version": 2'),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="schema_version 2 is not supported"):
        ContractSection.load(path)


@pytest.mark.unit
def test_MOD_007_deterministic_dump(tmp_path: Path) -> None:
    section = ContractSection.model_validate(_section())
    a, b = tmp_path / "a.json", tmp_path / "b.json"
    section.dump(a)
    section.dump(b)
    data = a.read_bytes()
    assert data == b.read_bytes()
    assert data.endswith(b"}\n") and b"\r\n" not in data
    text = data.decode("utf-8")
    assert text.index('"citations"') < text.index('"extraction"') < text.index('"fields"')
    assert text.index('"name": "name"') < text.index('"name": "size"')
    assert ContractSection.load(a) == ContractSection.load(b)


@pytest.mark.unit
def test_MOD_008_stable_finding_id() -> None:
    e1 = Evidence(kind="doc", page=3, quote="enum shade {Red,Green,Blue}")
    e2 = Evidence(kind="doc", page=5, quote='"color": "Grean",')
    a = Finding.make_id("SPEC_SELF_INCONSISTENCY", "S-2.2", "color", [e1, e2])
    b = Finding.make_id("SPEC_SELF_INCONSISTENCY", "S-2.2", "color", [e2, e1])
    assert a == b
    assert re.fullmatch(r"F-[0-9a-f]{8}", a)
    assert a != Finding.make_id("SPEC_SELF_INCONSISTENCY", "S-2.2", "size", [e1, e2])


@pytest.mark.unit
def test_MOD_009_issue_codes_match_catalog(repo_root: Path) -> None:
    documented = _doc_table_codes(repo_root, "## 6. Verification rule catalog", r"`(V\d_[A-Z_]+)`")
    assert set(get_args(IssueCode)) == documented


@pytest.mark.unit
def test_MOD_010_finding_types_match_catalog(repo_root: Path) -> None:
    documented = _doc_table_codes(
        repo_root, "**Finding types:**", r"`((?:SPEC|COMMUNITY|CLIENT)_[A-Z_]+)`"
    )
    assert set(get_args(FindingType)) == documented
