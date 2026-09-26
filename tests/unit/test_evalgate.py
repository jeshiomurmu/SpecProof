from pathlib import Path
from typing import Any

import pytest
import yaml

from specproof.evalgate import gate

THRESHOLDS = {
    "version": 1,
    "metrics": {
        "endpoint_coverage": {"min": 0.90, "target": 1.0},
        "quarantine_rate": {"max": 0.10, "target": 0.03},
    },
}


def _rate(value: float | None) -> dict[str, Any]:
    return {"numerator": 1, "denominator": 1, "value": value}


@pytest.mark.unit
def test_EVL_001_pass() -> None:
    result = gate({"endpoint_coverage": _rate(0.95), "quarantine_rate": _rate(0.05)}, THRESHOLDS)
    assert result.passed
    assert [r["verdict"] for r in result.rows] == ["PASS", "PASS"]


@pytest.mark.unit
def test_EVL_002_min_fail_names_metric() -> None:
    result = gate({"endpoint_coverage": _rate(0.8999), "quarantine_rate": _rate(0.0)}, THRESHOLDS)
    assert not result.passed
    assert [r["metric"] for r in result.rows if r["verdict"] == "FAIL"] == ["endpoint_coverage"]


@pytest.mark.unit
def test_EVL_003_max_fail() -> None:
    result = gate({"endpoint_coverage": _rate(1.0), "quarantine_rate": _rate(0.1001)}, THRESHOLDS)
    assert [r["metric"] for r in result.rows if r["verdict"] == "FAIL"] == ["quarantine_rate"]


@pytest.mark.unit
def test_EVL_004_missing_metric_fails() -> None:
    result = gate({"endpoint_coverage": {"value": None, "reason": "no contracts"}}, THRESHOLDS)
    rows = {r["metric"]: r for r in result.rows}
    assert not result.passed
    assert rows["endpoint_coverage"]["reason"] == "missing: no contracts"
    assert rows["quarantine_rate"]["reason"] == "missing: metric not computed"


@pytest.mark.unit
def test_EVL_005_result_lists_every_threshold(repo_root: Path) -> None:
    thresholds = yaml.safe_load((repo_root / "eval" / "thresholds.yaml").read_text("utf-8"))
    result = gate({}, thresholds)
    assert [r["metric"] for r in result.rows] == sorted(thresholds["metrics"])
    for row in result.rows:
        assert set(row) == {"metric", "value", "threshold", "verdict", "reason"}
    assert result.to_json()["passed"] is False
