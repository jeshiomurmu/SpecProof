"""I/O orchestration for `specproof verify`: read inputs, run the pure engine, write results."""

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from specproof import __version__
from specproof.config import RULES_VERSION, Paths
from specproof.models.manifest import InputRef, ManifestRecord, Producer, append_record
from specproof.models.verification import VerificationResult
from specproof.util.hashing import sha256_file
from specproof.util.io_json import dump_json, load_json
from specproof.util.io_pages import read_pages, read_section_lines
from specproof.verify.engine import has_extraction_errors, verify_section

log = logging.getLogger(__name__)


def select_contracts(paths: Paths, sections: list[str] | None, chapter: int | None) -> list[Path]:
    """Contract files to verify, sorted by section id; filtered by --section or --chapter."""
    files = sorted(paths.contract_dir.glob("S-*.json")) if paths.contract_dir.exists() else []
    if sections:
        wanted = set(sections)
        files = [f for f in files if f.stem in wanted]
        for missing in sorted(wanted - {f.stem for f in files}):
            log.warning("%s: no contract file", missing)
    elif chapter is not None:
        files = [f for f in files if f.stem.split("-")[1].split(".")[0] == str(chapter)]
    return files


def _summary(result: VerificationResult) -> str:
    def count(category: str) -> int:
        return sum(1 for i in result.issues if i.category == category)

    return (
        f"{result.section_id} attempt {result.attempt}: "
        f"{count('extraction')} extraction, {count('sample_conflict')} sample conflicts, "
        f"{count('info')} info"
    )


def _write(paths: Paths, contract: Path, result: VerificationResult, pages: list[int]) -> None:
    data = result.model_dump(mode="json")
    targets = [
        paths.verification_dir / f"{result.section_id}.json",
        paths.verification_dir / f"{result.section_id}_attempt{result.attempt}.json",
    ]
    producer = Producer(
        kind="deterministic", tool="specproof", version=__version__, rules_version=RULES_VERSION
    )
    inputs = [
        InputRef(path=paths.rel(contract), sha256=sha256_file(contract)),
        InputRef(path=paths.rel(paths.pages), sha256=sha256_file(paths.pages), pages=pages),
    ]
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    for target in targets:
        dump_json(target, data)
        record = ManifestRecord(
            artifact=paths.rel(target),
            sha256=sha256_file(target),
            stage="verify",
            producer=producer,
            inputs=inputs,
            created_at=now,
        )
        append_record(paths.manifest, record)


def record_contract(paths: Paths, contract: Path, raw: str) -> None:
    """Lineage for an AI-produced contract: producer, mode, prompt version, attempt."""
    try:
        data = json.loads(raw)
        extraction = data.get("extraction", {}) if isinstance(data, dict) else {}
    except ValueError:
        extraction = {}
    producer_name = str(extraction.get("producer", ""))
    attempt = extraction.get("attempt")
    producer = Producer(
        kind="ibm-bob" if producer_name == "ibm-bob" else "external",
        tool=producer_name or None,
        mode=extraction.get("mode"),
        prompt_version=extraction.get("prompt_version"),
        attempt=attempt if isinstance(attempt, int) else None,
        bob_task_ref=extraction.get("bob_task_ref"),
    )
    append_record(
        paths.manifest,
        ManifestRecord(
            artifact=paths.rel(contract),
            sha256=sha256_file(contract),
            stage="extract",
            producer=producer,
            inputs=[
                InputRef(
                    path=paths.rel(paths.sections_index), sha256=sha256_file(paths.sections_index)
                )
            ],
            created_at=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        ),
    )


def run_verify(
    paths: Paths, sections: list[str] | None, chapter: int | None
) -> list[VerificationResult]:
    """Verify the selected contracts and write their results; returns results in id order."""
    contracts = select_contracts(paths, sections, chapter)
    if not contracts:
        log.info("verify: no contracts to verify")
        return []
    index: dict[str, dict[str, Any]] = {e["section_id"]: e for e in load_json(paths.sections_index)}
    pages = {p.number: p.text for p in read_pages(paths.pages)}
    lines = read_section_lines(paths.sections_text)
    results = []
    for contract in contracts:
        entry = index.get(contract.stem)
        if entry is None:
            log.error("%s: not in sections_index.json; skipped", contract.stem)
            continue
        raw = contract.read_text(encoding="utf-8")
        record_contract(paths, contract, raw)
        result = verify_section(raw, entry, pages, lines.get(contract.stem, []))
        span = list(range(int(entry["page_start"]), int(entry["page_end"]) + 1))
        _write(paths, contract, result, span)
        log.info("%s", _summary(result))
        results.append(result)
    failing = sum(1 for r in results if has_extraction_errors(r))
    log.info("verify: %d sections, %d with extraction errors", len(results), failing)
    return results
