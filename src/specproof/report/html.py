"""Render the self-contained HTML evidence pack. Pure: state in, HTML string out."""

import json
from dataclasses import dataclass, field
from importlib import resources
from typing import Any

from jinja2 import Environment, PackageLoader, select_autoescape

from specproof.report.metrics import pct

HERO = (
    ("endpoint_coverage", "Endpoint sections extracted"),
    ("citation_grounding_rate", "Items with a grounded citation"),
    ("final_verified_rate", "Sections verified after the loop"),
    ("audited_precision", "Audited precision (blind sample)"),
)


@dataclass
class ReportState:
    """Everything the report shows; every number comes from metrics or findings."""

    spec_title: str
    source_sha: str
    metrics: dict[str, dict[str, Any]]
    findings: list[dict[str, Any]]
    endpoints: list[dict[str, Any]] = field(default_factory=list)
    funnel: list[dict[str, Any]] = field(default_factory=list)
    lineage: list[dict[str, Any]] = field(default_factory=list)
    content_hash: str = ""
    repo_url: str = "../../"


def fraction(metric: dict[str, Any] | None) -> str:
    """'a/b (x%)' with truncation, or 'pending - reason' when there is no value."""
    if not metric or metric.get("value") is None:
        reason = (metric or {}).get("reason", "not computed")
        return f"pending - {reason}"
    if "denominator" in metric:
        return f"{metric['numerator']}/{metric['denominator']} ({pct(float(metric['value']))})"
    return str(metric["value"])


def _ci(metric: dict[str, Any] | None) -> str:
    if not metric or "ci95" not in metric:
        return ""
    lo, hi = metric["ci95"]
    return f"95% CI {pct(lo)} - {pct(hi)}"


def content() -> dict[str, Any]:
    """Static report content shipped with the package (build map, rules, limitations)."""
    text = resources.files("specproof.report").joinpath("content.json").read_text("utf-8")
    data: dict[str, Any] = json.loads(text)
    return data


def _summary(findings: list[dict[str, Any]], prefix: str) -> dict[str, Any]:
    group = [f for f in findings if str(f["type"]).startswith(prefix)]
    counts: dict[str, int] = {}
    for f in group:
        counts[f["type"]] = counts.get(f["type"], 0) + 1
    confirmed = sum(1 for f in group if f["review"]["status"] == "CONFIRMED")
    return {"total": len(group), "confirmed": confirmed, "by_type": sorted(counts.items())}


def render(state: ReportState) -> str:
    """The evidence pack as one HTML document with inline CSS and JS only."""
    env = Environment(
        loader=PackageLoader("specproof.report", "templates"),
        autoescape=select_autoescape(["html", "j2"]),
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )
    metrics = state.metrics
    confirmed = sum(
        int(metrics.get(f"{k}_confirmed", {}).get("total", 0))
        for k in ("spec_findings", "community_discrepancies", "client_findings")
    )
    hero = [
        {"label": label, "value": fraction(metrics.get(key)), "note": _ci(metrics.get(key))}
        for key, label in HERO
    ]
    hero.append(
        {
            "label": "Human-confirmed findings",
            "value": str(confirmed),
            "note": "CONFIRMED in review",
        }
    )
    findings = sorted(state.findings, key=lambda f: (f["type"], f["id"]))
    return env.get_template("report.html.j2").render(
        state=state,
        hero=hero,
        findings=findings,
        types=sorted({f["type"] for f in findings}),
        severities=[
            s
            for s in ("high", "medium", "low", "info")
            if any(f["severity"] == s for f in findings)
        ],
        spec=_summary(findings, "SPEC_"),
        community=_summary(findings, "COMMUNITY_"),
        client=_summary(findings, "CLIENT_"),
        content=content(),
    )


def render_landing(spec_title: str, metrics: dict[str, dict[str, Any]], repo_url: str = "") -> str:
    """The one-screen landing page with three hero numbers from metrics.json."""
    env = Environment(
        loader=PackageLoader("specproof.report", "templates"),
        autoescape=select_autoescape(["html", "j2"]),
        keep_trailing_newline=True,
    )
    numbers = [{"label": label, "value": fraction(metrics.get(key))} for key, label in HERO[:3]]
    return env.get_template("landing.html.j2").render(
        spec_title=spec_title, numbers=numbers, repo_url=repo_url
    )
