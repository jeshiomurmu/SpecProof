"""I/O orchestration for `specproof classify`: statuses, spec findings and feedback files."""

import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from specproof import __version__
from specproof.config import RULES_VERSION, Paths
from specproof.loop.classify import classify, extraction_errors
from specproof.loop.feedback import render_feedback
from specproof.models.contract import ContractSection
from specproof.models.findings import Finding
from specproof.models.manifest import InputRef, ManifestRecord, Producer, append_record
from specproof.models.verification import VerificationResult
from specproof.util.hashing import sha256_file
from specproof.util.io_json import dump_json, load_json, write_bytes_atomic

log = logging.getLogger(__name__)


def _result(path: Path) -> VerificationResult:
    return VerificationResult.model_validate(load_json(path))


def _contract(path: Path) -> ContractSection | None:
    try:
        return ContractSection.load(path)
    except (OSError, ValueError):
        return None


def _record(paths: Paths, artifact: Path, inputs: list[Path]) -> None:
    producer = Producer(
        kind="deterministic", tool="specproof", version=__version__, rules_version=RULES_VERSION
    )
    append_record(
        paths.manifest,
        ManifestRecord(
            artifact=paths.rel(artifact),
            sha256=sha256_file(artifact),
            stage="classify",
            producer=producer,
            inputs=[InputRef(path=paths.rel(p), sha256=sha256_file(p)) for p in inputs],
            created_at=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        ),
    )


def run_classify(paths: Paths) -> dict[str, dict[str, Any]]:
    """Classify every latest verification result and write status, findings and feedback."""
    latest = (
        sorted(p for p in paths.verification_dir.glob("S-*.json") if "_attempt" not in p.stem)
        if paths.verification_dir.exists()
        else []
    )
    index = {e["section_id"]: e for e in load_json(paths.sections_index)} if latest else {}
    status: dict[str, dict[str, Any]] = {}
    findings: list[Finding] = []
    feedback_written: list[Path] = []
    for path in latest:
        result = _result(path)
        sid = result.section_id
        contract = _contract(paths.contract_dir / f"{sid}.json")
        prev_path = paths.verification_dir / f"{sid}_attempt{result.attempt - 1}.json"
        previous = _result(prev_path) if result.attempt > 1 and prev_path.exists() else None
        state, section_findings = classify(result, contract, previous)
        status[sid] = {
            "attempt": result.attempt,
            "extraction_errors": len(extraction_errors(result)),
            "status": state,
        }
        findings.extend(section_findings)
        target = paths.feedback_dir / f"{sid}.md"
        if state == "NEEDS_RETRY":
            entry = index.get(sid, {"page_start": 0, "page_end": 0})
            span = (int(entry["page_start"]), int(entry["page_end"]))
            text = render_feedback(result, contract, span)
            write_bytes_atomic(target, text.encode("utf-8"))
            feedback_written.append(target)
            _record(paths, target, [path])
        elif target.exists():
            target.unlink()
        log.info("%s: %s (attempt %d)", sid, state, result.attempt)
    dump_json(paths.status, status)
    dump_json(
        paths.spec_findings,
        [f.model_dump(mode="json") for f in sorted(findings, key=lambda f: f.id)],
    )
    _record(paths, paths.status, latest)
    _record(paths, paths.spec_findings, latest)
    return status
