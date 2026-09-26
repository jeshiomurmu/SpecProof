"""I/O orchestration for `specproof report`: findings.json, SARIF, HTML and landing page."""

import logging
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from specproof import __version__
from specproof.config import Paths
from specproof.io_metrics import all_findings, run_metrics
from specproof.models.manifest import (
    InputRef,
    ManifestRecord,
    Producer,
    append_record,
    load_manifest,
)
from specproof.report.html import ReportState, render, render_landing
from specproof.report.sarif import to_sarif
from specproof.util.hashing import sha256_bytes, sha256_file
from specproof.util.io_json import dump_json, dumps_json, load_json, write_bytes_atomic

log = logging.getLogger(__name__)
TRUSTED = frozenset({"VERIFIED", "VERIFIED_WITH_SPEC_FINDINGS"})


def _csv_reviews(paths: Paths) -> dict[str, dict[str, str]]:
    import csv

    if not paths.findings_review.exists():
        return {}
    with paths.findings_review.open(encoding="utf-8", newline="") as handle:
        return {row["finding_id"]: row for row in csv.DictReader(handle)}


def reviewed_findings(paths: Paths) -> list[dict[str, Any]]:
    """All findings with the human review decisions from findings_review.csv applied."""
    decisions = _csv_reviews(paths)
    out = []
    for finding in all_findings(paths):
        row = decisions.get(str(finding["id"]))
        if row and row.get("status", "").strip().upper() in ("CONFIRMED", "REJECTED"):
            finding = {
                **finding,
                "review": {
                    "status": row["status"].strip().upper(),
                    "reviewer": row.get("reviewer") or None,
                    "note": row.get("note") or None,
                },
            }
        out.append(finding)
    return out


def _attempt_errors(paths: Paths) -> dict[str, dict[int, int]]:
    """section -> attempt -> number of extraction errors."""
    out: dict[str, dict[int, int]] = {}
    if not paths.verification_dir.exists():
        return out
    for path in sorted(paths.verification_dir.glob("S-*_attempt*.json")):
        sid, _, attempt = path.stem.partition("_attempt")
        issues = load_json(path).get("issues", [])
        errors = sum(
            1 for i in issues if i["category"] == "extraction" and i["severity"] == "error"
        )
        out.setdefault(sid, {})[int(attempt)] = errors
    return out


def funnel(paths: Paths, status: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    """Sections without extraction errors after attempt 1, retry 1, retry 2, and final."""
    attempts = _attempt_errors(paths)
    total = len(status)
    if total == 0:
        return []
    steps = []
    for k, label in ((1, "After attempt 1"), (2, "After retry 1"), (3, "After retry 2")):
        ok = sum(
            1 for sid in status if any(n <= k and e == 0 for n, e in attempts.get(sid, {}).items())
        )
        steps.append({"label": label, "verified": ok, "total": total})
    final = sum(1 for row in status.values() if row["status"] in TRUSTED)
    steps.append({"label": "Final (terminal status)", "verified": final, "total": total})
    return steps


def endpoints(paths: Paths, status: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    """One row per endpoint section of the index, extracted or not."""
    index = load_json(paths.sections_index) if paths.sections_index.exists() else []
    rows = []
    for entry in index:
        if entry["kind"] != "endpoint":
            continue
        sid = entry["section_id"]
        result_path = paths.verification_dir / f"{sid}.json"
        counts = load_json(result_path)["counts"] if result_path.exists() else {}
        row = status.get(sid, {})
        rows.append(
            {
                "section_id": sid,
                "method": entry.get("method_hint") or "",
                "path": entry.get("path_hint") or "",
                "status": row.get("status", "NOT_EXTRACTED"),
                "attempts": row.get("attempt", 0),
                "items": counts.get("items", 0),
                "grounded": counts.get("grounded", 0),
                "row_ok": counts.get("row_ok", 0),
                "row_checked": counts.get("row_checked", 0),
            }
        )
    return rows


def _spec_title(paths: Paths) -> str:
    lock = paths.root / "sources" / "sources.lock.yaml"
    if lock.exists():
        for source in yaml.safe_load(lock.read_text(encoding="utf-8")).get("sources", []):
            if source.get("id") == "unifi_spec_pdf":
                return str(source["description"]).split(" (PDF)")[0]
    return "the specification"


def _source_sha(paths: Paths) -> str:
    record = next((r for r in load_manifest(paths.manifest) if r.stage == "ingest"), None)
    return record.inputs[0].sha256 if record and record.inputs else "unknown"


def repo_url(root: Path) -> str:
    """The https URL of the origin remote, or "" when there is none."""
    done = subprocess.run(
        ["git", "remote", "get-url", "origin"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    url = done.stdout.strip().removesuffix(".git")
    return url if url.startswith("https://") else ""


def _record(paths: Paths, artifact: Path) -> None:
    append_record(
        paths.manifest,
        ManifestRecord(
            artifact=paths.rel(artifact),
            sha256=sha256_file(artifact),
            stage="report",
            producer=Producer(kind="deterministic", tool="specproof", version=__version__),
            inputs=[InputRef(path=paths.rel(paths.metrics), sha256=sha256_file(paths.metrics))],
            created_at=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        ),
    )


def run_report(paths: Paths) -> Path:
    """Recompute metrics, then write findings.json, findings.sarif, the report and landing."""
    metrics = run_metrics(paths)
    findings = reviewed_findings(paths)
    dump_json(paths.findings_all, findings)
    dump_json(paths.sarif, to_sarif(findings))
    status = load_json(paths.status) if paths.status.exists() else {}
    manifest = load_manifest(paths.manifest)
    state = ReportState(
        spec_title=_spec_title(paths),
        source_sha=_source_sha(paths),
        metrics=metrics,
        findings=findings,
        endpoints=endpoints(paths, status),
        funnel=funnel(paths, status),
        lineage=[
            {
                "artifact": r.artifact,
                "sha256": r.sha256,
                "stage": r.stage,
                "producer": r.producer.kind,
            }
            for r in manifest
        ],
        content_hash=sha256_bytes((dumps_json(metrics) + dumps_json(findings)).encode("utf-8")),
    )
    write_bytes_atomic(paths.report_html, render(state).encode("utf-8"))
    landing = render_landing(state.spec_title, metrics, repo_url(paths.root))
    write_bytes_atomic(paths.root / "demo" / "index.html", landing.encode("utf-8"))
    for artifact in (paths.findings_all, paths.sarif, paths.report_html):
        _record(paths, artifact)
    log.info(
        "report: %s (%d bytes)", paths.rel(paths.report_html), paths.report_html.stat().st_size
    )
    return paths.report_html
