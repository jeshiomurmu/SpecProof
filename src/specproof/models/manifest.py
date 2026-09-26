"""Lineage records in artifacts/manifest.json (DATA_GOVERNANCE_AND_LINEAGE section 4)."""

from pathlib import Path
from typing import Any

from pydantic import BaseModel

from specproof.util.io_json import dump_json, load_json


class ManifestRecord(BaseModel):
    """One produced artifact with its hash, stage, producer and inputs."""

    artifact: str
    sha256: str
    stage: str
    producer: dict[str, Any]
    inputs: list[dict[str, Any]]
    created_at: str


def load_manifest(path: Path) -> list[ManifestRecord]:
    """Read the manifest; a missing file is an empty manifest."""
    if not path.exists():
        return []
    return [ManifestRecord.model_validate(r) for r in load_json(path)]


def append_record(path: Path, record: ManifestRecord) -> None:
    """Add record, replacing any older record for the same artifact; keep sorted by artifact.

    An older record that differs only in created_at is kept, so unchanged reruns leave the
    manifest byte-identical.
    """
    existing = load_manifest(path)
    old = next((r for r in existing if r.artifact == record.artifact), None)
    if old is not None and old.model_dump(exclude={"created_at"}) == record.model_dump(
        exclude={"created_at"}
    ):
        return
    records = [r for r in existing if r.artifact != record.artifact]
    records.append(record)
    records.sort(key=lambda r: r.artifact)
    dump_json(path, [r.model_dump() for r in records])


def find_record(path: Path, artifact: str) -> ManifestRecord | None:
    """Return the record for artifact, if any."""
    return next((r for r in load_manifest(path) if r.artifact == artifact), None)
