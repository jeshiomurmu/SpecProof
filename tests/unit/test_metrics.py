import json
from pathlib import Path
from typing import Any

import pytest

from specproof.report.metrics import State, compute_metrics, pct, trunc4, wilson

FX06 = Path(__file__).resolve().parent.parent / "fixtures" / "state_metrics.json"


@pytest.fixture(scope="module")
def metrics() -> dict[str, Any]:
    return compute_metrics(State.from_dict(json.loads(FX06.read_text(encoding="utf-8"))))


# Hand-computed from FX-06 (see the fixture):
#   endpoint sections 4 (S-2.2..S-2.5), with a contract 3 (S-2.5 missing)
#   items 3+11+9+5=28, grounded 3+11+7+5=26; row_checked 0+4+5+1=10, row_ok 0+4+3+1=8
#   row candidates = row_checked 10 + ROW_NOT_FOUND 1 = 11; rows detected 10, gaps 1
#   contracts 4, V1-invalid 1; samples 4, parsed 3
#   sections 4; first pass: 0 extraction errors at attempt 1 = S-2.1, S-2.4 -> 2
#   final VERIFIED* = 3; quarantined 1; attempts 1+2+3+1 = 7
#   attempt-1 extraction issues 4; still present at the end: (id, CITATION_NOT_FOUND) -> fixed 3
EXPECTED = {
    "endpoint_coverage": (3, 4, 0.75),
    "citation_presence_rate": (28, 28, 1.0),
    "citation_grounding_rate": (26, 28, 0.9285),
    "row_check_applicability": (10, 11, 0.909),
    "row_consistency_rate": (8, 10, 0.8),
    "field_coverage": (9, 10, 0.9),
    "schema_valid_rate": (3, 4, 0.75),
    "sample_parse_rate": (3, 4, 0.75),
    "first_pass_verified_rate": (2, 4, 0.5),
    "final_verified_rate": (3, 4, 0.75),
    "quarantine_rate": (1, 4, 0.25),
    "mean_attempts": (7, 4, 1.75),
    "issues_fixed_by_loop": (3, 4, 0.75),
    "audited_precision": (38, 40, 0.95),
    "audited_miss_rate": (1, 12, 0.0833),
    "verifier_false_accept": (1, 36, 0.0277),
    "determinism": (20, 20, 1.0),
}


@pytest.mark.unit
@pytest.mark.parametrize("key", sorted(EXPECTED))
def test_MET_001_formulas(metrics: dict[str, Any], key: str) -> None:
    numerator, denominator, value = EXPECTED[key]
    assert (metrics[key]["numerator"], metrics[key]["denominator"]) == (numerator, denominator)
    assert metrics[key]["value"] == value


@pytest.mark.unit
def test_MET_001_derived_and_counts(metrics: dict[str, Any]) -> None:
    assert metrics["loop_lift"]["value"] == 0.25
    assert metrics["spec_findings_candidate"] == {
        "by_type": {"SPEC_MALFORMED_SAMPLE": 1, "SPEC_SELF_INCONSISTENCY": 1},
        "total": 2,
    }
    assert metrics["spec_findings_confirmed"]["total"] == 1
    assert metrics["community_discrepancies_candidate"]["total"] == 2
    assert metrics["community_discrepancies_confirmed"]["total"] == 0
    assert metrics["client_findings_confirmed"]["by_type"] == {"CLIENT_SAMPLE_REJECTED": 1}
    assert metrics["manual_minutes_per_endpoint"]["value"] == 12.0
    assert metrics["unit_test_coverage"]["value"] == 0.9137
    assert metrics["audited_precision"]["ci95"] == pytest.approx([0.8350, 0.9862], abs=1e-4)


@pytest.mark.unit
def test_MET_002_every_rate_has_denominator(metrics: dict[str, Any]) -> None:
    for key, metric in metrics.items():
        if "value" in metric and "numerator" in metric:
            assert isinstance(metric["denominator"], int), key
    missing = compute_metrics(State.from_dict({"index": []}))
    assert missing["endpoint_coverage"]["value"] is None
    assert missing["endpoint_coverage"]["denominator"] == 0
    assert "reason" in missing["audited_precision"]
    assert missing["bobcoins_per_verified_endpoint"]["value"] is None


@pytest.mark.unit
def test_MET_003_truncation_never_rounds_up() -> None:
    assert pct(0.89999) == "89.9%"
    assert pct(0.29) == "29.0%"
    assert pct(1.0) == "100.0%"
    assert trunc4(2, 3) == 0.6666
    assert trunc4(1, 0) is None


@pytest.mark.unit
@pytest.mark.parametrize(
    ("c", "n", "lo", "hi"),
    [(38, 40, 0.8350, 0.9862), (40, 40, 0.9124, 1.0), (36, 40, 0.7695, 0.9604)],
)
def test_MET_004_wilson(c: int, n: int, lo: float, hi: float) -> None:
    assert wilson(c, n) == pytest.approx((lo, hi), abs=1e-4)
