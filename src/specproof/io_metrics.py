"""I/O for metrics, the eval gate and the blind audit: load state, write results."""

import csv
import io
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from specproof import __version__
from specproof.audit import SHEET_COLUMNS, contract_items, sample_items, score
from specproof.config import Paths
from specproof.evalgate import GateResult, gate
from specproof.models.contract import ContractSection
from specproof.models.manifest import InputRef, ManifestRecord, Producer, append_record
from specproof.report.metrics import State, compute_metrics
from specproof.util.hashing import sha256_file
from specproof.util.io_json import dump_json, load_json, write_bytes_atomic

log = logging.getLogger(__name__)


class AuditExistsError(Exception):
    """The audit sample already exists and must never be re-drawn."""


def _json(path: Path, default: Any) -> Any:
    return load_json(path) if path.exists() else default


def _csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _results(paths: Paths, suffix: str) -> dict[str, dict[str, Any]]:
    if not paths.verification_dir.exists():
        return {}
    out: dict[str, dict[str, Any]] = {}
    for path in sorted(paths.verification_dir.glob("S-*.json")):
        stem = path.stem
        if suffix and stem.endswith(suffix):
            out[stem.removesuffix(suffix)] = load_json(path)
        elif not suffix and "_attempt" not in stem:
            out[stem] = load_json(path)
    return out


def all_findings(paths: Paths) -> list[dict[str, Any]]:
    """Spec, community and client findings, sorted by id."""
    findings: list[dict[str, Any]] = [
        *_json(paths.spec_findings, []),
        *_json(paths.community_findings, []),
        *_json(paths.conformance_findings, {}).get("findings", []),
    ]
    return sorted(findings, key=lambda f: str(f["id"]))


def reviews(paths: Paths) -> dict[str, str]:
    """Human finding decisions from eval/audit/findings_review.csv."""
    return {
        row["finding_id"]: row["status"].strip().upper()
        for row in _csv(paths.findings_review)
        if row.get("status", "").strip().upper() in ("CONFIRMED", "REJECTED")
    }


def load_state(paths: Paths) -> State:
    """Gather every metric input from the artifacts that exist now."""
    coverage = _json(paths.work / "coverage.json", None)
    minutes = [float(r["minutes"]) for r in _csv(paths.manual_baseline) if r.get("minutes")]
    contracts = (
        sorted(p.stem for p in paths.contract_dir.glob("S-*.json"))
        if paths.contract_dir.exists()
        else []
    )
    return State(
        index=_json(paths.sections_index, []),
        contracts=contracts,
        latest=_results(paths, ""),
        first=_results(paths, "_attempt1"),
        status=_json(paths.status, {}),
        findings=all_findings(paths),
        reviews=reviews(paths),
        audit=_json(paths.audit_score, None),
        manual_minutes=minutes or None,
        determinism=_json(paths.artifacts / "determinism.json", None),
        coverage_percent=coverage["totals"]["percent_covered"] if coverage else None,
    )


def _record(paths: Paths, artifact: Path, stage: str) -> None:
    append_record(
        paths.manifest,
        ManifestRecord(
            artifact=paths.rel(artifact),
            sha256=sha256_file(artifact),
            stage=stage,
            producer=Producer(kind="deterministic", tool="specproof", version=__version__),
            inputs=[
                InputRef(path=paths.rel(p), sha256=sha256_file(p))
                for p in (paths.status, paths.sections_index)
                if p.exists()
            ],
            created_at=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        ),
    )


def run_metrics(paths: Paths) -> dict[str, dict[str, Any]]:
    """Compute metrics.json from the current artifacts."""
    metrics = compute_metrics(load_state(paths))
    dump_json(paths.metrics, metrics)
    _record(paths, paths.metrics, "metrics")
    return metrics


def run_eval(paths: Paths, thresholds: Path) -> GateResult:
    """Recompute metrics, gate them, and write eval_result.json."""
    metrics = run_metrics(paths)
    result = gate(metrics, yaml.safe_load(thresholds.read_text(encoding="utf-8")))
    dump_json(paths.eval_result, result.to_json())
    _record(paths, paths.eval_result, "eval")
    return result


def _contracts(paths: Paths) -> list[ContractSection]:
    contracts = []
    for path in sorted(paths.contract_dir.glob("S-*.json")) if paths.contract_dir.exists() else []:
        try:
            contracts.append(ContractSection.load(path))
        except (OSError, ValueError) as exc:
            log.warning("%s: skipped in audit sample (%s)", path.name, str(exc).splitlines()[0])
    return contracts


def run_audit_sample(paths: Paths, n: int, seed: int) -> int:
    """Draw and write the blind audit sheet once; refuses to overwrite."""
    if paths.audit_sample.exists():
        raise AuditExistsError(f"{paths.rel(paths.audit_sample)} exists; never re-draw the sample")
    picked = sample_items(contract_items(_contracts(paths)), n, seed)
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=SHEET_COLUMNS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(item.row() for item in picked)
    write_bytes_atomic(paths.audit_sample, buffer.getvalue().encode("utf-8"))
    return len(picked)


def run_audit_score(paths: Paths) -> dict[str, Any]:
    """Score the filled audit sheet and write eval/audit/audit_score.json."""
    rows = _csv(paths.audit_sample)
    extraction: dict[str, set[str]] = {
        sid: {str(i.get("field")) for i in r.get("issues", []) if i.get("category") == "extraction"}
        for sid, r in _results(paths, "").items()
    }
    result = score(rows, extraction)
    dump_json(paths.audit_score, result)
    return result
