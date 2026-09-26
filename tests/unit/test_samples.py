import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from specproof.models.contract import ContractSection
from specproof.verify.samples import build_request_schema, extract_payload, validate_samples

Good = Callable[[str], dict[str, Any]]
GOLDEN = Path(__file__).resolve().parent.parent / "fixtures" / "golden" / "schema_S-2.2.json"


def _with_request_payload(good: Good, payload: str) -> ContractSection:
    data = good("S-2.2")
    data["samples"]["request"]["raw"] = (
        f"curl '{{{{host}}}}/api/v1/widgets'\n --data-raw '{payload}'"
    )
    return ContractSection.model_validate(data)


def _codes(contract: ContractSection) -> list[tuple[str, str | None]]:
    issues, _counts = validate_samples(contract)
    return [(i.code, i.field) for i in issues]


@pytest.mark.unit
def test_SMP_001_curl_payload_across_line_breaks(good: Good) -> None:
    raw = good("S-2.2")["samples"]["request"]["raw"]
    assert json.loads(extract_payload(raw)) == {
        "name": "Bolt",
        "color": "Grean",
        "size": 3,
        "notes": "fragile",
    }
    assert extract_payload('  {"a": 1}  ') == '{"a": 1}'


@pytest.mark.unit
def test_SMP_002_malformed_sample(good: Good) -> None:
    contract = ContractSection.model_validate(good("S-2.4"))
    issues, counts = validate_samples(contract)
    assert [(i.code, i.category, i.severity) for i in issues] == [
        ("V3_SAMPLE_UNPARSEABLE", "sample_conflict", "error")
    ]
    assert counts == {"samples": 1, "samples_parsed": 0}


@pytest.mark.unit
def test_SMP_003_required_missing_is_warning(good: Good) -> None:
    contract = _with_request_payload(good, '{"color": "Red", "size": 3}')
    issues, _ = validate_samples(contract)
    assert [(i.code, i.field, i.severity) for i in issues] == [
        ("V3_REQUIRED_MISSING", "name", "warning")
    ]


@pytest.mark.unit
def test_SMP_004_type_mismatch(good: Good) -> None:
    contract = _with_request_payload(good, '{"name": "Bolt", "color": "Red", "size": "3"}')
    assert _codes(contract) == [("V3_TYPE_MISMATCH", "size")]


@pytest.mark.unit
def test_SMP_005_enum_violation(good: Good) -> None:
    contract = ContractSection.model_validate(good("S-2.2"))
    issues, counts = validate_samples(contract)
    assert [(i.code, i.field, i.category) for i in issues] == [
        ("V3_ENUM_VIOLATION", "color", "sample_conflict")
    ]
    assert issues[0].evidence is not None and issues[0].evidence.page == 5
    assert counts == {"samples": 2, "samples_parsed": 2}


@pytest.mark.unit
def test_SMP_006_unknown_key_is_info(good: Good) -> None:
    contract = _with_request_payload(good, '{"name": "Bolt", "color": "Red", "extra": 1}')
    issues, _ = validate_samples(contract)
    assert [(i.code, i.field, i.severity) for i in issues] == [
        ("V3_UNKNOWN_FIELD", "extra", "info")
    ]


@pytest.mark.unit
def test_SMP_007_placeholders_raise_nothing(good: Good) -> None:
    payload = '{"name": "example@*.com", "color": "Red", "notes": "wHFmHR******kD6wHg"}'
    assert _codes(_with_request_payload(good, payload)) == []


@pytest.mark.unit
def test_SMP_008_response_envelope_and_fields(good: Good) -> None:
    ok = ContractSection.model_validate(good("S-2.3"))
    assert _codes(ok) == []

    bad = good("S-2.3")
    bad["samples"]["response"]["raw"] = '{"msg": "success", "data": [{"id": "w-1", "name": "B",'
    bad["samples"]["response"]["raw"] += ' "color": "Red", "created_at": "yesterday"}]}'
    assert _codes(ContractSection.model_validate(bad)) == [
        ("V3_REQUIRED_MISSING", "code"),
        ("V3_TYPE_MISMATCH", "created_at"),
    ]


@pytest.mark.unit
def test_SMP_010_bodiless_curl_is_not_a_json_sample(good: Good) -> None:
    data = good("S-2.2")
    data["samples"]["request"]["raw"] = (
        "curl -XGET '{{host}}/api/v1/widgets'\n -H 'Authorization: x'"
    )
    contract = ContractSection.model_validate(data)
    issues, counts = validate_samples(contract)
    assert [i.code for i in issues if i.field is None] == []
    assert counts == {"samples": 1, "samples_parsed": 1}
    assert extract_payload("curl -XDELETE '{{host}}/x'") is None


@pytest.mark.unit
@pytest.mark.parametrize(
    "raw",
    [
        '{"code": "SUCCESS", "msg": "success"}',
        '{"code": "SUCCESS", "msg": "success", "data": null}',
    ],
    ids=["no-data", "null-data"],
)
def test_SMP_011_response_without_data_is_fine(good: Good, raw: str) -> None:
    data = good("S-2.3")
    data["samples"]["response"]["raw"] = raw
    assert _codes(ContractSection.model_validate(data)) == []


@pytest.mark.unit
def test_SMP_012_short_data_flag(good: Good) -> None:
    raw = "curl -XPUT '{{host}}/x'\n -d '{\n \"name\": \"Bolt\"\n }'"
    assert extract_payload(raw) == '{\n "name": "Bolt"\n }'
    assert extract_payload("curl '{{host}}/x' --data '{\"a\": 1}'") == '{"a": 1}'
    assert extract_payload("curl -H 'x-id: 1' '{{host}}/x'") is None


@pytest.mark.unit
def test_SMP_013_undocumented_body_is_not_type_checked(good: Good) -> None:
    data = good("S-2.3")
    data["samples"]["request"] = {
        "raw": "curl -XPUT '{{host}}/x'\n --data '[\n \"abcd\"\n ]'",
        "citation": {"page": 6, "quote": "Request URL: /api/v1/widgets/:id"},
    }
    assert _codes(ContractSection.model_validate(data)) == []


@pytest.mark.unit
def test_SMP_014_empty_data_is_no_body() -> None:
    assert extract_payload("curl -XPUT '{{host}}/x'\n --data ''") is None


@pytest.mark.unit
def test_SMP_015_layout_wrapped_string_is_joined(good: Good) -> None:
    data = good("S-2.3")
    data["samples"]["response"]["raw"] = (
        '{\n "code": "SUCCESS",\n "msg": "success",\n "data": {"id": "w-1", "name": "Very long\n'
        '   name", "color": "Red", "created_at": 1727000000}\n}'
    )
    assert _codes(ContractSection.model_validate(data)) == []


@pytest.mark.unit
def test_SMP_016_null_is_allowed_for_any_documented_type(good: Good) -> None:
    data = good("S-2.3")
    data["samples"]["response"]["raw"] = (
        '{"code": "SUCCESS", "msg": "success", "data": {"id": "w-1", "name": null, '
        '"color": "Red", "created_at": null}}'
    )
    assert _codes(ContractSection.model_validate(data)) == []


def _with_response(good: Good, fields: list[dict[str, Any]], raw: str) -> ContractSection:
    data = good("S-2.3")
    data["fields"] = [f for f in data["fields"] if f["location"] != "response"] + fields
    data["samples"]["response"]["raw"] = raw
    return ContractSection.model_validate(data)


def _resp_field(name: str, type_: str, type_raw: str) -> dict[str, Any]:
    return {
        "name": name,
        "location": "response",
        "required": True,
        "type": type_,
        "type_raw": type_raw,
        "citation": {"page": 6, "quote": "Request URL: /api/v1/widgets/:id"},
    }


@pytest.mark.unit
def test_SMP_017_data_row_describes_the_envelope(good: Good) -> None:
    array_data = _resp_field("Data", "array", "Array[Object]")
    ok = _with_response(good, [array_data], '{"code": "S", "msg": "m", "data": [{"x": 1}]}')
    assert _codes(ok) == []
    wrong = _with_response(good, [array_data], '{"code": "S", "msg": "m", "data": {"x": 1}}')
    assert _codes(wrong) == [("V3_TYPE_MISMATCH", "Data")]


@pytest.mark.unit
def test_SMP_018_undocumented_response_data_is_not_type_checked(good: Good) -> None:
    contract = _with_response(good, [], '{"code": "S", "msg": "m", "data": "success"}')
    assert _codes(contract) == []


@pytest.mark.unit
def test_SMP_009_schema_build_golden(good: Good) -> None:
    schema = build_request_schema(ContractSection.model_validate(good("S-2.2")))
    assert schema == json.loads(GOLDEN.read_text(encoding="utf-8"))
