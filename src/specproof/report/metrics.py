"""Every metric in docs/EVALUATION_FRAMEWORK.md section 2, with explicit denominators.

Pure: build a State from artifacts elsewhere, then compute. Values are truncated, never
rounded up, and a zero denominator gives null, never 1.0.
"""

import math
import statistics
from dataclasses import dataclass, field
from decimal import ROUND_FLOOR, Decimal
from fractions import Fraction
from typing import Any

TRUSTED = frozenset({"VERIFIED", "VERIFIED_WITH_SPEC_FINDINGS"})
Z95 = 1.959963984540054
FINDING_GROUPS = {
    "spec_findings": "SPEC_",
    "community_discrepancies": "COMMUNITY_",
    "client_findings": "CLIENT_",
}
_CATEGORY = "category"


@dataclass
class State:
    """Everything the metrics need, already loaded from artifacts."""

    index: list[dict[str, Any]] = field(default_factory=list)
    contracts: list[str] = field(default_factory=list)
    latest: dict[str, dict[str, Any]] = field(default_factory=dict)
    first: dict[str, dict[str, Any]] = field(default_factory=dict)
    status: dict[str, dict[str, Any]] = field(default_factory=dict)
    findings: list[dict[str, Any]] = field(default_factory=list)
    reviews: dict[str, str] = field(default_factory=dict)
    audit: dict[str, int] | None = None
    manual_minutes: list[float] | None = None
    determinism: dict[str, int] | None = None
    coverage_percent: float | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "State":
        """Build a State from a plain dict (keys as in the dataclass; missing keys default)."""
        known = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        return cls(**known)


def trunc4(numerator: int, denominator: int) -> float | None:
    """numerator/denominator floored to 4 decimals; None when the denominator is 0."""
    if denominator == 0:
        return None
    return math.floor(Fraction(numerator, denominator) * 10000) / 10000


def pct(value: float) -> str:
    """Percentage with one decimal, floored: 0.89999 -> '89.9%'."""
    scaled = (Decimal(str(value)) * 100).quantize(Decimal("0.1"), rounding=ROUND_FLOOR)
    return f"{scaled}%"


def wilson(correct: int, n: int, z: float = Z95) -> tuple[float, float]:
    """Wilson score 95% interval for correct/n."""
    if n == 0:
        return (0.0, 1.0)
    p = correct / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    margin = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, center - margin), min(1.0, center + margin))


def rate(numerator: int, denominator: int) -> dict[str, Any]:
    """A rate with its visible numerator and denominator (null + reason when nothing to count)."""
    if denominator == 0:
        return {
            "numerator": numerator,
            "denominator": 0,
            "value": None,
            "reason": "denominator is 0 (no inputs yet)",
        }
    return {
        "numerator": numerator,
        "denominator": denominator,
        "value": trunc4(numerator, denominator),
    }


def missing(reason: str) -> dict[str, Any]:
    """A metric that cannot be computed yet, with the reason."""
    return {"value": None, "reason": reason}


def _issues(result: dict[str, Any], category: str | None = None) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = result.get("issues", [])
    return [i for i in issues if category is None or i.get(_CATEGORY) == category]


def _extraction_errors(result: dict[str, Any]) -> list[dict[str, Any]]:
    return [i for i in _issues(result, "extraction") if i.get("severity") == "error"]


def _count(key: str, results: dict[str, dict[str, Any]]) -> int:
    return sum(int(r.get("counts", {}).get(key, 0)) for r in results.values())


def _code_count(code: str, results: dict[str, dict[str, Any]]) -> int:
    return sum(1 for r in results.values() for i in _issues(r) if i.get("code") == code)


def extraction_metrics(s: State) -> dict[str, dict[str, Any]]:
    """Section 2.1: extraction quality."""
    endpoints = {e["section_id"] for e in s.index if e.get("kind") == "endpoint"}
    items = _count("items", s.latest)
    checked = _count("row_checked", s.latest)
    detected = _count("rows_detected", s.latest)
    invalid = sum(
        1
        for r in s.latest.values()
        if any(i.get("code") == "V1_SCHEMA_INVALID" for i in _issues(r))
    )
    return {
        "endpoint_coverage": rate(len(endpoints & set(s.contracts)), len(endpoints)),
        "citation_presence_rate": rate(items, items),
        "citation_grounding_rate": rate(_count("grounded", s.latest), items),
        "row_check_applicability": rate(
            checked, checked + _code_count("V2_ROW_NOT_FOUND", s.latest)
        ),
        "row_consistency_rate": rate(_count("row_ok", s.latest), checked),
        "field_coverage": rate(detected - _code_count("V5_COVERAGE_GAP", s.latest), detected),
        "schema_valid_rate": rate(len(s.latest) - invalid, len(s.latest)),
        "sample_parse_rate": rate(_count("samples_parsed", s.latest), _count("samples", s.latest)),
    }


def loop_metrics(s: State) -> dict[str, dict[str, Any]]:
    """Section 2.2: loop effectiveness."""
    sections = len(s.status)
    first_ok = sum(1 for sid in s.status if sid in s.first and not _extraction_errors(s.first[sid]))
    final_ok = sum(1 for row in s.status.values() if row["status"] in TRUSTED)
    quarantined = sum(1 for row in s.status.values() if row["status"] == "QUARANTINED")
    attempts = sum(int(row["attempt"]) for row in s.status.values())
    before = {
        (sid, i["code"], i.get("field"))
        for sid, r in s.first.items()
        for i in _extraction_errors(r)
    }
    after = {
        (sid, i["code"], i.get("field"))
        for sid, r in s.latest.items()
        for i in _extraction_errors(r)
    }
    lift: float | None = None
    if sections:
        exact = Fraction(final_ok - first_ok, sections)
        lift = math.floor(exact * 10000) / 10000
    return {
        "first_pass_verified_rate": rate(first_ok, sections),
        "final_verified_rate": rate(final_ok, sections),
        "loop_lift": {"value": lift, "formula": "final_verified_rate - first_pass_verified_rate"},
        "quarantine_rate": rate(quarantined, sections),
        "mean_attempts": rate(attempts, sections),
        "issues_fixed_by_loop": rate(len(before - after), len(before)),
    }


def accuracy_metrics(s: State) -> dict[str, dict[str, Any]]:
    """Section 2.3: blind-audit accuracy (human-verified)."""
    if s.audit is None or not s.audit.get("n"):
        reason = "blind audit not scored yet (specproof audit-score, T13)"
        return {
            k: missing(reason)
            for k in ("audited_precision", "audited_miss_rate", "verifier_false_accept")
        }
    a = s.audit
    precision = rate(a["correct"], a["n"])
    precision["ci95"] = list(wilson(a["correct"], a["n"]))
    return {
        "audited_precision": precision,
        "audited_miss_rate": rate(a["sections_with_miss"], a["sections"]),
        "verifier_false_accept": rate(a["verifier_passed_incorrect"], a["verifier_passed"]),
    }


def _by_type(findings: list[dict[str, Any]]) -> dict[str, Any]:
    counts: dict[str, int] = {}
    for f in findings:
        counts[f["type"]] = counts.get(f["type"], 0) + 1
    return {"by_type": dict(sorted(counts.items())), "total": len(findings)}


def finding_metrics(s: State) -> dict[str, dict[str, Any]]:
    """Section 2.4: finding counts; confirmed = human CONFIRMED in findings_review.csv."""
    out: dict[str, dict[str, Any]] = {}
    for key, prefix in FINDING_GROUPS.items():
        group = [f for f in s.findings if str(f["type"]).startswith(prefix)]
        confirmed = [f for f in group if s.reviews.get(f["id"]) == "CONFIRMED"]
        out[f"{key}_candidate"] = _by_type(group)
        out[f"{key}_confirmed"] = _by_type(confirmed)
    return out


def productivity_metrics(s: State) -> dict[str, dict[str, Any]]:
    """Section 2.5: only the manual baseline is computable from repo files."""
    bob = "comes from IBM Bob task exports and screenshots (T08); not machine-readable here"
    if s.manual_minutes:
        manual: dict[str, Any] = {
            "value": float(statistics.median(s.manual_minutes)),
            "n": len(s.manual_minutes),
            "method": (
                "median of hand transcriptions, single tester (EVALUATION_FRAMEWORK section 5)"
            ),
        }
    else:
        manual = missing("eval/audit/manual_baseline.csv not recorded yet")
    return {
        "manual_minutes_per_endpoint": manual,
        "specproof_minutes_per_endpoint": missing(bob),
        "time_reduction_factor": missing("needs specproof_minutes_per_endpoint"),
        "bobcoins_per_verified_endpoint": missing(bob),
        "projected_manual_hours_full_spec": missing("reported in the report with its range"),
    }


def engineering_metrics(s: State) -> dict[str, dict[str, Any]]:
    """Section 2.6: determinism and test coverage."""
    determinism = (
        rate(s.determinism["identical"], s.determinism["total"])
        if s.determinism
        else missing("artifacts/determinism.json not written yet (E2E-002 / E2E-R03)")
    )
    coverage = (
        {
            "value": math.floor(Decimal(str(s.coverage_percent)) * 100) / 10000,
            "source": "coverage.py",
        }
        if s.coverage_percent is not None
        else missing("artifacts/work/coverage.json not found; run make check")
    )
    return {"determinism": determinism, "unit_test_coverage": coverage}


def compute_metrics(s: State) -> dict[str, dict[str, Any]]:
    """All metrics, keyed by the catalog names."""
    out: dict[str, dict[str, Any]] = {}
    for part in (
        extraction_metrics,
        loop_metrics,
        accuracy_metrics,
        finding_metrics,
        productivity_metrics,
        engineering_metrics,
    ):
        out.update(part(s))
    return out
