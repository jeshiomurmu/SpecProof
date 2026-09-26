import json
from pathlib import Path

import pytest

from specproof.report.readme import END, START, results_table, update_readme

FX06 = Path(__file__).resolve().parent.parent / "fixtures" / "state_metrics.json"
METRICS = {
    "endpoint_coverage": {"numerator": 108, "denominator": 108, "value": 1.0},
    "citation_grounding_rate": {"numerator": 1406, "denominator": 1406, "value": 1.0},
    "first_pass_verified_rate": {"numerator": 97, "denominator": 116, "value": 0.8362},
    "final_verified_rate": {"numerator": 115, "denominator": 116, "value": 0.9913},
    "quarantine_rate": {"numerator": 1, "denominator": 116, "value": 0.0086},
    "audited_precision": {"value": None, "reason": "blind audit not scored yet"},
    "spec_findings_candidate": {"by_type": {}, "total": 30},
    "spec_findings_confirmed": {"by_type": {}, "total": 2},
    "community_discrepancies_candidate": {"by_type": {}, "total": 30},
    "community_discrepancies_confirmed": {"by_type": {}, "total": 0},
    "client_findings_candidate": {"by_type": {}, "total": 3},
    "client_findings_confirmed": {"by_type": {}, "total": 1},
    "manual_minutes_per_endpoint": {"value": 12.0, "n": 3},
}
README = f"# Title\n\nintro\n\n{START}\nold table\n{END}\n\nrest\n"


@pytest.mark.unit
def test_RDM_001_table_from_metrics() -> None:
    table = results_table(METRICS)
    assert "| Endpoint sections extracted | 108/108 (100.0%) |" in table
    assert "97/116 (83.6%) → 115/116 (99.1%)" in table
    assert "| Audited precision (blind sample) | pending (blind audit not scored yet) |" in table
    assert "2 confirmed of 30 candidates" in table
    assert "12.0 min per endpoint (n=3, single tester)" in table


@pytest.mark.unit
def test_RDM_002_idempotent_and_confined_to_markers() -> None:
    once = update_readme(README, METRICS)
    twice = update_readme(once, METRICS)
    assert once == twice
    assert once.startswith("# Title\n\nintro\n\n") and once.endswith(f"{END}\n\nrest\n")
    assert "old table" not in once


@pytest.mark.unit
def test_RDM_003_missing_markers_fail_loudly() -> None:
    with pytest.raises(ValueError, match="RESULTS"):
        update_readme("# no markers\n", METRICS)


@pytest.mark.unit
def test_RDM_004_works_on_real_metric_shape() -> None:
    from specproof.report.metrics import State, compute_metrics

    metrics = compute_metrics(State.from_dict(json.loads(FX06.read_text(encoding="utf-8"))))
    table = results_table(metrics)
    assert "3/4 (75.0%)" in table
    assert "38/40 (95.0%, 95% CI 83.4% to 98.6%)" in table
