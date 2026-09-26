"""Lineage records in artifacts/manifest.json (DATA_GOVERNANCE_AND_LINEAGE section 4)."""

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict

from specproof.util.io_json import dump_json, load_json


class Producer(BaseModel):
    """Who produced an artifact: deterministic tooling, an IBM Bob extraction, or another
    external producer (e.g. hand-written test fixtures)."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["deterministic", "ibm-bob", "external"]
    tool: str | None = None
    version: str | None = None
    rules_version: str | None = None
    extractor: str | None = None
    extractor_version: str | None = None
    mode: str | None = None
    prompt_version: str | None = None
    attempt: int | None = None
    bob_task_ref: str | None = None


class InputRef(BaseModel):
    """One input of an artifact: a repo path or a pinned source, with its sha256."""

    model_config = ConfigDict(extra="forbid")

    sha256: str
    path: str | None = None
    source_id: str | None = None
    pages: list[int] | None = None


class ManifestRecord(BaseModel):
    """One produced artifact with its hash, stage, producer and inputs."""

    model_config = ConfigDict(extra="forbid")

    artifact: str
    sha256: str
    stage: str
    producer: Producer
    inputs: list[InputRef]
    created_at: str

    def content(self) -> dict[str, object]:
        """Return the record without its timestamp and without unset optional keys."""
        return self.model_dump(exclude={"created_at"}, exclude_none=True)


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
    if old is not None and old.content() == record.content():
        return
    records = [r for r in existing if r.artifact != record.artifact]
    records.append(record)
    records.sort(key=lambda r: r.artifact)
    dump_json(path, [r.model_dump(exclude_none=True) for r in records])


def find_record(path: Path, artifact: str) -> ManifestRecord | None:
    """Return the record for artifact, if any."""
    return next((r for r in load_manifest(path) if r.artifact == artifact), None)
