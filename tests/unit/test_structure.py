from collections.abc import Callable
from typing import Any

import pytest

from specproof.ingest.segment import Section
from specproof.models.contract import ContractSection
from specproof.models.verification import VerificationResult
from specproof.verify.grounding import SectionContext
from specproof.verify.structure import check_coverage, check_endpoint, detected_rows, norm_path

Good = Callable[[str], dict[str, Any]]
Run = Callable[[dict[str, Any] | str, str], VerificationResult]


@pytest.mark.unit
@pytest.mark.parametrize("raw", ["{not json", '{"schema_version": 1}', "[]"])
def test_STR_001_invalid_contract_is_v1_not_exception(run_verify: Run, raw: str) -> None:
    result = run_verify(raw, "S-2.2")
    assert [i.code for i in result.issues] == ["V1_SCHEMA_INVALID"]
    assert result.issues[0].category == "extraction"


@pytest.mark.unit
def test_STR_007_schema_error_names_the_field(run_verify: Run, good: Good) -> None:
    data = good("S-2.2")
    data["notes"] = ["an extra key"]
    data["fields"][0]["required"] = "sometimes"
    [issue] = run_verify(data, "S-2.2").issues
    assert issue.code == "V1_SCHEMA_INVALID"
    assert "notes: Extra inputs are not permitted" in issue.message
    assert "fields.0.required" in issue.message


@pytest.mark.unit
def test_STR_002_method_mismatch(good: Good, synthetic_sections: dict[str, Section]) -> None:
    contract = ContractSection.model_validate({**good("S-2.2"), "method": "PUT"})
    issues = check_endpoint(contract, synthetic_sections["S-2.2"].entry)
    assert [i.code for i in issues] == ["V4_METHOD_MISMATCH"]


@pytest.mark.unit
def test_STR_003_path_mismatch(good: Good, synthetic_sections: dict[str, Section]) -> None:
    contract = ContractSection.model_validate({**good("S-2.2"), "path": "/api/v1/gizmos"})
    issues = check_endpoint(contract, synthetic_sections["S-2.2"].entry)
    assert [i.code for i in issues] == ["V4_PATH_MISMATCH"]


@pytest.mark.unit
def test_STR_004_path_normalization(good: Good, synthetic_sections: dict[str, Section]) -> None:
    assert norm_path("api/v1/widgets/:id") == norm_path("/api/v1/widgets/{widget_id}")
    assert norm_path("/api/v1/widgets/?page=2") == "/api/v1/widgets"
    entry = {**synthetic_sections["S-2.3"].entry, "path_hint": "/api/v1/widgets/{widget_id}"}
    contract = ContractSection.model_validate({**good("S-2.3"), "path": "api/v1/widgets/:id"})
    assert check_endpoint(contract, entry) == []


@pytest.mark.unit
def test_STR_004_missing_path_hint_skips_path_check(
    good: Good, synthetic_sections: dict[str, Section]
) -> None:
    entry = {**synthetic_sections["S-2.2"].entry, "path_hint": None}
    contract = ContractSection.model_validate({**good("S-2.2"), "path": "/anything"})
    assert check_endpoint(contract, entry) == []


@pytest.mark.unit
def test_STR_005_coverage_gap(good: Good, section_ctx: Callable[[str], SectionContext]) -> None:
    data = good("S-2.2")
    data["fields"] = [f for f in data["fields"] if f["name"] != "size"]
    issues = check_coverage(section_ctx("S-2.2"), ContractSection.model_validate(data))
    assert [(i.code, i.field) for i in issues] == [("V5_COVERAGE_GAP", "size")]


@pytest.mark.unit
def test_STR_006_grounded_field_not_detected_as_row_is_not_flagged(
    good: Good, section_ctx: Callable[[str], SectionContext]
) -> None:
    ctx = section_ctx("S-2.2")
    assert set(detected_rows(ctx)) == {"Authorization", "name", "color", "size"}
    contract = ContractSection.model_validate(good("S-2.2"))
    assert "notes" in {f.name for f in contract.fields}
    assert check_coverage(ctx, contract) == []
