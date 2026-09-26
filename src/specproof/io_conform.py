"""I/O orchestration for `specproof conform`: inventory, mapping, model diff, sample replay."""

import logging
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from specproof import __version__
from specproof.config import Paths
from specproof.conformance.check import check_inventory
from specproof.conformance.inventory import scan_endpoints
from specproof.conformance.mapping import load_mappings
from specproof.conformance.models import ModelField, diff_model
from specproof.conformance.replay import generate, introspect, run_replay
from specproof.loop.status import verified_section_ids
from specproof.models.contract import ContractSection
from specproof.models.findings import Finding
from specproof.models.manifest import InputRef, ManifestRecord, Producer, append_record
from specproof.util.hashing import sha256_file
from specproof.util.io_json import dump_json, load_json, write_bytes_atomic

log = logging.getLogger(__name__)


def ensure_replay_venv(paths: Paths, client: Path) -> str:
    """Create artifacts/work/replay-venv with the client and pytest; return its python.

    This installs packages with pip (network), as architecture section 8 prescribes."""
    venv = paths.work / "replay-venv"
    python = venv / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    if not python.exists():
        subprocess.run([sys.executable, "-m", "venv", str(venv)], check=True)
        subprocess.run(
            [str(python), "-m", "pip", "install", "-q", "-e", str(client), "pytest"], check=True
        )
    return str(python)


def _label(paths: Paths, client: Path) -> str:
    try:
        return paths.rel(client.resolve())
    except ValueError:
        return client.name


def _record(paths: Paths, artifact: Path, inputs: list[Path]) -> None:
    append_record(
        paths.manifest,
        ManifestRecord(
            artifact=paths.rel(artifact),
            sha256=sha256_file(artifact),
            stage="conform",
            producer=Producer(kind="deterministic", tool="specproof", version=__version__),
            inputs=[
                InputRef(path=paths.rel(p), sha256=sha256_file(p)) for p in inputs if p.exists()
            ],
            created_at=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        ),
    )


def run_conform(paths: Paths, client: Path, python: str | None) -> dict[str, Any]:
    """Run C1-C3 and write artifacts/findings/conformance.json; returns its content."""
    client = client.resolve()
    label = _label(paths, client)
    verified = verified_section_ids(paths.status)
    contracts = {
        sid: ContractSection.load(paths.contract_dir / f"{sid}.json")
        for sid in verified
        if (paths.contract_dir / f"{sid}.json").exists()
    }
    index = load_json(paths.sections_index) if paths.sections_index.exists() else []
    refs = scan_endpoints(client)
    findings, uncheckable = check_inventory(refs, index, list(contracts.values()), label)
    mappings, mapping_errors = load_mappings(paths.mapping, client, set(verified))
    errors: list[dict[str, str]] = []
    all_findings: list[Finding] = list(findings)
    if mappings:
        interpreter = python or ensure_replay_venv(paths, client)
        described = introspect([m.model for m in mappings], interpreter, [client])
        for mapping in mappings:
            info = described.get(mapping.model, {"error": "not introspected"})
            if "error" in info:
                errors.append(
                    {"kind": "environment_error", "message": f"{mapping.model}: {info['error']}"}
                )
                continue
            fields: list[ModelField] = info["fields"]
            all_findings += diff_model(fields, mapping, contracts[mapping.section_id], label)
        write_bytes_atomic(paths.replay_test, generate(mappings, contracts).encode("utf-8"))
        replay_findings, replay_errors = run_replay(
            paths.replay_test, mappings, contracts, interpreter, [client], label
        )
        all_findings += replay_findings
        errors += replay_errors
    unique = {f.id: f for f in all_findings}
    result = {
        "errors": errors,
        "findings": [unique[k].model_dump(mode="json") for k in sorted(unique)],
        "inventory": [
            {
                "file": r.file,
                "line": r.line,
                "method": r.method,
                "path": r.path_norm,
                "dynamic": r.dynamic,
            }
            for r in refs
        ],
        "mapping_errors": mapping_errors,
        "uncheckable": uncheckable,
    }
    dump_json(paths.conformance_findings, result)
    if paths.mapping.exists():
        append_record(
            paths.manifest,
            ManifestRecord(
                artifact=paths.rel(paths.mapping),
                sha256=sha256_file(paths.mapping),
                stage="map",
                producer=Producer(kind="ibm-bob", mode="spec-auditor"),
                inputs=[InputRef(path=paths.rel(paths.status), sha256=sha256_file(paths.status))]
                if paths.status.exists()
                else [],
                created_at=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            ),
        )
    _record(paths, paths.conformance_findings, [paths.status, paths.mapping])
    if paths.replay_test.exists():
        _record(paths, paths.replay_test, [paths.mapping])
    log.info(
        "conform: %d call sites, %d findings, %d uncheckable, %d mapping errors, %d errors",
        len(refs),
        len(unique),
        len(uncheckable),
        len(mapping_errors),
        len(errors),
    )
    return result
