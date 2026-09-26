import json
import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
import yaml
from openapi_spec_validator import validate
from typer.testing import CliRunner

from specproof.cli import app
from specproof.compare.community import diff
from specproof.compare.openapi_export import export
from specproof.models.contract import ContractSection
from specproof.models.findings import Finding
from specproof.util.io_json import load_json

Good = Callable[[str], dict[str, Any]]
FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"
COMMUNITY = FIXTURES / "community_min.yaml"
LABEL = "artifacts/work/community_openapi.yaml"
ALL_VERIFIED = {f"S-2.{n}": "VERIFIED" for n in range(1, 5)}


def _contracts(good: Good) -> list[ContractSection]:
    return [ContractSection.model_validate(good(f"S-2.{n}")) for n in range(1, 5)]


def _findings(good: Good) -> list[Finding]:
    theirs = yaml.safe_load(COMMUNITY.read_text(encoding="utf-8"))
    ours = export(_contracts(good), sorted(ALL_VERIFIED))
    return diff(ours, theirs, COMMUNITY.read_text(encoding="utf-8"), LABEL)


def _by_type(findings: list[Finding], type_: str) -> list[Finding]:
    return [f for f in findings if f.type == type_]


@pytest.mark.integration
def test_CMP_001_export_is_valid_openapi(good: Good) -> None:
    spec = export(_contracts(good), sorted(ALL_VERIFIED))
    validate(spec)
    assert spec["openapi"] == "3.1.0"
    assert set(spec["paths"]) == {"/api/v1/widgets", "/api/v1/widgets/{id}"}
    assert set(spec["paths"]["/api/v1/widgets"]) == {"post", "delete"}
    assert "S-2.1" in spec["components"]["schemas"]
    body = spec["paths"]["/api/v1/widgets"]["post"]["requestBody"]["content"]
    schema = body["application/json"]["schema"]
    assert schema["required"] == ["color", "name"]
    assert schema["properties"]["size"]["x-specproof-citation"]["page"] == 4


@pytest.mark.integration
def test_CMP_002_exports_verified_sections_only(good: Good) -> None:
    spec = export(_contracts(good), ["S-2.1", "S-2.2", "S-2.4"])
    assert set(spec["paths"]) == {"/api/v1/widgets"}
    assert "S-2.3" not in json.dumps(spec)


@pytest.mark.integration
def test_CMP_003_path_normalization_is_not_a_diff(good: Good) -> None:
    missing = _by_type(_findings(good), "COMMUNITY_MISSING_ENDPOINT")
    assert [f.section_id for f in missing] == ["S-2.4"]


@pytest.mark.integration
def test_CMP_004_required_mismatch_with_pdf_citation(good: Good) -> None:
    [finding] = _by_type(_findings(good), "COMMUNITY_REQUIRED_MISMATCH")
    assert finding.section_id == "S-2.2"
    assert "`size`" in finding.title and "optional" in finding.title
    doc = [e for e in finding.evidence if e.kind == "doc"]
    code = [e for e in finding.evidence if e.kind == "code"]
    assert [(e.page, e.quote) for e in doc] == [
        (4, "size                  F       Integer   Size in millimetres.")
    ]
    assert code[0].file == LABEL
    assert code[0].snippet == "#/components/schemas/WidgetCreate/required"
    assert code[0].line is not None and code[0].line > 1


@pytest.mark.integration
def test_CMP_005_type_mismatch(good: Good) -> None:
    [finding] = _by_type(_findings(good), "COMMUNITY_TYPE_MISMATCH")
    assert (finding.section_id, "`name`" in finding.title) == ("S-2.2", True)


@pytest.mark.integration
def test_CMP_006_enum_mismatch(good: Good) -> None:
    [finding] = _by_type(_findings(good), "COMMUNITY_ENUM_MISMATCH")
    assert "`color`" in finding.title and "Blue" in finding.title


@pytest.mark.integration
def test_CMP_007_missing_endpoint(good: Good) -> None:
    [finding] = _by_type(_findings(good), "COMMUNITY_MISSING_ENDPOINT")
    assert "DELETE /api/v1/widgets" in finding.title
    assert [e.page for e in finding.evidence if e.kind == "doc"] == [7]


@pytest.mark.integration
def test_CMP_008_deterministic_and_complete(good: Good) -> None:
    first, second = _findings(good), _findings(good)
    assert [f.model_dump() for f in first] == [f.model_dump() for f in second]
    assert [f.id for f in first] == sorted(f.id for f in first)
    assert sorted(f.type for f in first) == [
        "COMMUNITY_ENUM_MISMATCH",
        "COMMUNITY_MISSING_ENDPOINT",
        "COMMUNITY_REQUIRED_MISMATCH",
        "COMMUNITY_TYPE_MISMATCH",
    ]


@pytest.mark.integration
def test_CMP_010_missing_and_extra_fields(good: Good) -> None:
    theirs = yaml.safe_load(COMMUNITY.read_text(encoding="utf-8"))
    props = theirs["components"]["schemas"]["WidgetCreate"]["properties"]
    del props["notes"]
    props["serial"] = {"type": "string"}
    text = yaml.safe_dump(theirs, sort_keys=False)
    ours = export(_contracts(good), sorted(ALL_VERIFIED))
    findings = diff(ours, yaml.safe_load(text), text, LABEL)
    missing = _by_type(findings, "COMMUNITY_MISSING_FIELD")
    extra = _by_type(findings, "COMMUNITY_EXTRA_FIELD")
    assert ["`notes`" in f.title for f in missing] == [True]
    assert [(f.severity, "`serial`" in f.title) for f in extra] == [("info", True)]
    assert [e.kind for e in extra[0].evidence] == ["code"]


@pytest.mark.integration
def test_CMP_011_path_parameter_case_follows_the_template(good: Good) -> None:
    data = good("S-2.3")
    data["fields"].append(
        {
            "name": "Id",
            "location": "path",
            "required": True,
            "type": "string",
            "type_raw": "String",
            "citation": {"page": 6, "quote": "Request URL: /api/v1/widgets/:id"},
        }
    )
    data["fields"].append(
        {
            "name": "stray",
            "location": "path",
            "required": True,
            "type": "string",
            "type_raw": "String",
            "citation": {"page": 6, "quote": "Request URL: /api/v1/widgets/:id"},
        }
    )
    spec = export([ContractSection.model_validate(data)], ["S-2.3"])
    validate(spec)
    params = spec["paths"]["/api/v1/widgets/{id}"]["get"]["parameters"]
    assert [(p["in"], p["name"]) for p in params] == [("path", "id")]


@pytest.mark.integration
def test_CMP_009_cli_export_and_compare(workspace: Path) -> None:
    shutil.copytree(FIXTURES / "contracts_good", workspace / "artifacts" / "contract")
    shutil.copyfile(COMMUNITY, workspace / "artifacts" / "work" / "community_openapi.yaml")
    runner = CliRunner()
    runner.invoke(app, ["verify", "--report-only"])
    runner.invoke(app, ["classify"])
    assert runner.invoke(app, ["export-openapi"]).exit_code == 0
    exported = (workspace / "artifacts" / "openapi.specproof.yaml").read_bytes()
    assert b"\r\n" not in exported and b"x-specproof-section: S-2.2" in exported
    assert runner.invoke(app, ["compare", "--community"]).exit_code == 0
    findings = load_json(workspace / "artifacts" / "findings" / "community.json")
    assert len(findings) == 4
    manifest = {r["artifact"] for r in load_json(workspace / "artifacts" / "manifest.json")}
    assert {"artifacts/openapi.specproof.yaml", "artifacts/findings/community.json"} <= manifest
