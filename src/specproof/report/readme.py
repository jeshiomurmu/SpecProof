"""Generate the README results table from metrics.json (numbers are never hand-typed)."""

from typing import Any

from specproof.report.metrics import pct

START = "<!-- RESULTS:START -->"
END = "<!-- RESULTS:END -->"


def _pending(metric: dict[str, Any] | None) -> str:
    return f"pending ({(metric or {}).get('reason', 'not computed')})"


def _fraction(metric: dict[str, Any] | None) -> str:
    if not metric or metric.get("value") is None or "denominator" not in metric:
        return _pending(metric)
    return f"{metric['numerator']}/{metric['denominator']} ({pct(float(metric['value']))})"


def _precision(metric: dict[str, Any] | None) -> str:
    if not metric or metric.get("value") is None:
        return _pending(metric)
    lo, hi = metric.get("ci95", [None, None])
    ci = f", 95% CI {pct(lo)[:-1]}% to {pct(hi)[:-1]}%" if lo is not None else ""
    return f"{metric['numerator']}/{metric['denominator']} ({pct(float(metric['value']))}{ci})"


def _findings(metrics: dict[str, dict[str, Any]], key: str) -> str:
    confirmed = metrics.get(f"{key}_confirmed", {}).get("total", 0)
    candidates = metrics.get(f"{key}_candidate", {}).get("total", 0)
    return f"{confirmed} confirmed of {candidates} candidates"


def _baseline(metric: dict[str, Any] | None) -> str:
    if not metric or metric.get("value") is None:
        return _pending(metric)
    return f"{metric['value']} min per endpoint (n={metric.get('n', '?')}, single tester)"


def results_table(metrics: dict[str, dict[str, Any]]) -> str:
    """The Markdown results table, every value taken from metrics."""
    rows = [
        ("Endpoint sections extracted", _fraction(metrics.get("endpoint_coverage"))),
        (
            "Contract items with a citation found verbatim on the cited page",
            _fraction(metrics.get("citation_grounding_rate")),
        ),
        (
            "Sections verified: first pass → after the self-correction loop",
            f"{_fraction(metrics.get('first_pass_verified_rate'))} → "
            f"{_fraction(metrics.get('final_verified_rate'))}",
        ),
        ("Sections quarantined", _fraction(metrics.get("quarantine_rate"))),
        ("Audited precision (blind sample)", _precision(metrics.get("audited_precision"))),
        ("Spec self-inconsistencies and sample defects", _findings(metrics, "spec_findings")),
        ("Community OpenAPI discrepancies", _findings(metrics, "community_discrepancies")),
        ("Client conformance issues (py-unifi-access)", _findings(metrics, "client_findings")),
        ("Manual transcription baseline", _baseline(metrics.get("manual_minutes_per_endpoint"))),
    ]
    lines = ["| Metric | Value |", "|---|---|", *(f"| {name} | {value} |" for name, value in rows)]
    return "\n".join(lines)


def update_readme(text: str, metrics: dict[str, dict[str, Any]]) -> str:
    """Replace the text between the RESULTS markers; idempotent."""
    start = text.find(START)
    end = text.find(END)
    if start < 0 or end < start:
        raise ValueError(f"README needs the {START} and {END} markers around the results table")
    return text[: start + len(START)] + "\n" + results_table(metrics) + "\n" + text[end:]
