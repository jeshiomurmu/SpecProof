"""Eval gate: compare metrics.json against eval/thresholds.yaml (read-only, protected)."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class GateResult:
    """Per-metric verdicts, sorted by metric name; passed only if every verdict is PASS."""

    rows: list[dict[str, Any]]

    @property
    def passed(self) -> bool:
        """True when no row failed."""
        return all(r["verdict"] == "PASS" for r in self.rows)

    def to_json(self) -> dict[str, Any]:
        """The eval_result.json document."""
        return {"passed": self.passed, "results": self.rows}


def _verdict(value: float, threshold: dict[str, Any]) -> tuple[str, str]:
    if "min" in threshold and value < threshold["min"]:
        return "FAIL", f"{value} < min {threshold['min']}"
    if "max" in threshold and value > threshold["max"]:
        return "FAIL", f"{value} > max {threshold['max']}"
    return "PASS", ""


def gate(metrics: dict[str, dict[str, Any]], thresholds: dict[str, Any]) -> GateResult:
    """Check every threshold; a missing or null metric fails with its reason."""
    rows = []
    for name, threshold in sorted(thresholds.get("metrics", {}).items()):
        metric = metrics.get(name)
        value = metric.get("value") if metric else None
        if value is None:
            reason = (metric or {}).get("reason", "metric not computed")
            verdict, why = "FAIL", f"missing: {reason}"
        else:
            verdict, why = _verdict(float(value), threshold)
        rows.append(
            {
                "metric": name,
                "value": value,
                "threshold": threshold,
                "verdict": verdict,
                "reason": why,
            }
        )
    return GateResult(rows=rows)
