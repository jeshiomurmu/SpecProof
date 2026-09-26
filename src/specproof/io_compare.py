"""I/O orchestration for `export-openapi` and `compare --community`."""

import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml
from openapi_spec_validator import validate

from specproof import __version__
from specproof.compare.community import diff
from specproof.compare.openapi_export import export
from specproof.config import Paths
from specproof.loop.status import verified_section_ids
from specproof.models.contract import ContractSection
from specproof.models.manifest import InputRef, ManifestRecord, Producer, append_record
from specproof.util.hashing import sha256_file
from specproof.util.io_json import dump_json, write_bytes_atomic

log = logging.getLogger(__name__)


class ExportInvalidError(Exception):
    """The exported OpenAPI document failed validation."""


def dump_yaml(path: Path, data: Any) -> None:
    """Write YAML with sorted keys, UTF-8 and LF line endings, atomically."""
    text = yaml.safe_dump(data, sort_keys=True, allow_unicode=True, width=100)
    write_bytes_atomic(path, text.encode("utf-8"))


def _record(paths: Paths, artifact: Path, stage: str, inputs: list[Path]) -> None:
    append_record(
        paths.manifest,
        ManifestRecord(
            artifact=paths.rel(artifact),
            sha256=sha256_file(artifact),
            stage=stage,
            producer=Producer(kind="deterministic", tool="specproof", version=__version__),
            inputs=[InputRef(path=paths.rel(p), sha256=sha256_file(p)) for p in inputs],
            created_at=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        ),
    )


def run_export(paths: Paths) -> dict[str, Any]:
    """Export VERIFIED(+findings) contracts to artifacts/openapi.specproof.yaml."""
    verified = verified_section_ids(paths.status)
    files = [paths.contract_dir / f"{sid}.json" for sid in verified]
    contracts = [ContractSection.load(f) for f in files if f.exists()]
    spec = export(contracts, verified)
    try:
        validate(spec)
    except Exception as exc:
        raise ExportInvalidError(str(exc).splitlines()[0]) from exc
    dump_yaml(paths.openapi_export, spec)
    _record(
        paths, paths.openapi_export, "export", [paths.status, *[f for f in files if f.exists()]]
    )
    log.info("export-openapi: %d verified sections, %d paths", len(verified), len(spec["paths"]))
    return spec


def run_compare(paths: Paths) -> int:
    """Diff the export against the community spec; write findings/community.json."""
    ours = yaml.safe_load(paths.openapi_export.read_text(encoding="utf-8"))
    text = paths.community.read_text(encoding="utf-8")
    findings = diff(ours, yaml.safe_load(text), text, paths.rel(paths.community))
    dump_json(paths.community_findings, [f.model_dump(mode="json") for f in findings])
    _record(paths, paths.community_findings, "compare", [paths.openapi_export, paths.community])
    counts: dict[str, int] = {}
    for finding in findings:
        counts[finding.type] = counts.get(finding.type, 0) + 1
    log.info("compare: %d findings %s", len(findings), dict(sorted(counts.items())))
    return len(findings)
