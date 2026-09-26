from collections.abc import Callable
from typing import Any

import pytest
from fixtures.mutations import EXPECTED_CODE, mutate

from specproof.models.verification import RULE_ORDER, VerificationResult
from specproof.util.io_json import dumps_json

Good = Callable[[str], dict[str, Any]]
Run = Callable[[dict[str, Any] | str, str], VerificationResult]
GOOD_IDS = ["S-2.1", "S-2.2", "S-2.3", "S-2.4"]


def _extraction_codes(result: VerificationResult) -> list[str]:
    return [i.code for i in result.issues if i.category == "extraction"]


@pytest.mark.integration
@pytest.mark.parametrize("section_id", GOOD_IDS)
def test_ENG_001_good_contracts_have_no_extraction_issues(
    run_verify: Run, good: Good, section_id: str
) -> None:
    assert _extraction_codes(run_verify(good(section_id), section_id)) == []


@pytest.mark.integration
def test_ENG_001_expected_non_extraction_issues(run_verify: Run, good: Good) -> None:
    s22 = run_verify(good("S-2.2"), "S-2.2")
    assert [(i.code, i.field) for i in s22.issues] == [
        ("V2_ROW_NOT_FOUND", "notes"),
        ("V3_ENUM_VIOLATION", "color"),
    ]
    s24 = run_verify(good("S-2.4"), "S-2.4")
    assert [i.code for i in s24.issues] == ["V3_SAMPLE_UNPARSEABLE"]


@pytest.mark.integration
def test_ENG_002_issue_order(run_verify: Run, good: Good) -> None:
    contract = mutate(mutate(good("S-2.2"), "wrong_method"), "flip_required")
    contract["fields"] = [f for f in contract["fields"] if f["name"] != "size"]
    issues = run_verify(contract, "S-2.2").issues
    keys = [(RULE_ORDER.index(i.code), i.field or "", i.code) for i in issues]
    assert keys == sorted(keys)
    assert [i.code for i in issues] == [
        "V2_ROW_MISMATCH",
        "V2_ROW_NOT_FOUND",
        "V3_ENUM_VIOLATION",
        "V3_UNKNOWN_FIELD",
        "V4_METHOD_MISMATCH",
        "V5_COVERAGE_GAP",
    ]


@pytest.mark.integration
@pytest.mark.parametrize("section_id", GOOD_IDS)
def test_ENG_003_deterministic_bytes(run_verify: Run, good: Good, section_id: str) -> None:
    first = dumps_json(run_verify(good(section_id), section_id).model_dump(mode="json"))
    second = dumps_json(run_verify(good(section_id), section_id).model_dump(mode="json"))
    assert first == second


@pytest.mark.integration
@pytest.mark.parametrize("kind", sorted(EXPECTED_CODE))
def test_ENG_004_mutation_matrix(run_verify: Run, good: Good, kind: str) -> None:
    result = run_verify(mutate(good("S-2.2"), kind), "S-2.2")
    assert _extraction_codes(result) == [EXPECTED_CODE[kind]]


@pytest.mark.integration
def test_ENG_005_counts(run_verify: Run, good: Good) -> None:
    assert run_verify(good("S-2.2"), "S-2.2").counts == {
        "items": 11,
        "grounded": 11,
        "row_checked": 4,
        "row_ok": 4,
        "samples": 2,
        "samples_parsed": 2,
    }
    assert run_verify(good("S-2.4"), "S-2.4").counts == {
        "items": 5,
        "grounded": 5,
        "row_checked": 1,
        "row_ok": 1,
        "samples": 1,
        "samples_parsed": 0,
    }
    fabricated = run_verify(mutate(good("S-2.2"), "fabricate_quote"), "S-2.2")
    assert fabricated.counts["grounded"] == 10
