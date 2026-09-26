"""SpecProof command-line interface (architecture section 10)."""

import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

import typer

app = typer.Typer(help="SpecProof: verified, cited contracts from document-only API specs.")
log = logging.getLogger("specproof")


def _stub(task: str) -> None:
    log.warning("not implemented (%s)", task)


def _now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


@app.callback()
def main(verbose: Annotated[bool, typer.Option("--verbose", "-v")] = False) -> None:
    """Configure logging for every command."""
    logging.basicConfig(level=logging.DEBUG if verbose else logging.INFO, format="%(message)s")


@app.command()
def fetch(lock: Path = Path("sources/sources.lock.yaml")) -> None:
    """Download pinned sources and verify their SHA-256."""
    from specproof.sources.fetch import FetchError, fetch_all

    try:
        fetch_all(lock, Path.cwd())
    except FetchError as exc:
        log.error("%s", exc)
        raise typer.Exit(1) from exc


@app.command()
def ingest(extractor: str = "auto") -> None:
    """Extract page text from the spec PDF into artifacts/work/pages.jsonl."""
    from specproof import __version__
    from specproof.config import Paths
    from specproof.ingest.extractors import select_extractor
    from specproof.models.manifest import ManifestRecord, append_record, find_record
    from specproof.util.hashing import sha256_file
    from specproof.util.io_pages import write_pages

    paths = Paths.from_root(Path.cwd())
    if not paths.spec_pdf.exists():
        log.error("missing %s; run `specproof fetch` first", paths.rel(paths.spec_pdf))
        raise typer.Exit(2)
    try:
        chosen = select_extractor(extractor)
    except (RuntimeError, ValueError) as exc:
        log.error("%s", exc)
        raise typer.Exit(2) from exc
    pdf_sha = sha256_file(paths.spec_pdf)
    producer = {
        "kind": "deterministic",
        "tool": "specproof",
        "version": __version__,
        "extractor": chosen.name,
        "extractor_version": chosen.version(),
    }
    inputs = [{"path": paths.rel(paths.spec_pdf), "sha256": pdf_sha, "source_id": "unifi_spec_pdf"}]
    artifact = paths.rel(paths.pages)
    previous = find_record(paths.manifest, artifact)
    if (
        previous is not None
        and paths.pages.exists()
        and previous.producer == producer
        and previous.inputs == inputs
        and previous.sha256 == sha256_file(paths.pages)
    ):
        log.info("ingest: cached (%s, pdf %s)", chosen.name, pdf_sha[:12])
        return
    pages = chosen.extract(paths.spec_pdf)
    write_pages(paths.pages, pages)
    record = ManifestRecord(
        artifact=artifact,
        sha256=sha256_file(paths.pages),
        stage="ingest",
        producer=producer,
        inputs=inputs,
        created_at=_now(),
    )
    append_record(paths.manifest, record)
    log.info("ingest: %d pages with %s", len(pages), chosen.name)


@app.command()
def segment() -> None:
    """Split pages into sections and write artifacts/sections_index.json."""
    from specproof import __version__
    from specproof.config import Paths
    from specproof.ingest.segment import segment as run_segment
    from specproof.models.manifest import ManifestRecord, append_record
    from specproof.util.hashing import sha256_file
    from specproof.util.io_json import dump_json, write_jsonl
    from specproof.util.io_pages import read_pages

    paths = Paths.from_root(Path.cwd())
    if not paths.pages.exists():
        log.error("missing %s; run `specproof ingest` first", paths.rel(paths.pages))
        raise typer.Exit(2)
    sections = run_segment(read_pages(paths.pages))
    dump_json(paths.sections_index, [s.entry for s in sections])
    write_jsonl(
        paths.sections_text, [{"id": s.entry["section_id"], "text": s.text} for s in sections]
    )
    inputs = [{"path": paths.rel(paths.pages), "sha256": sha256_file(paths.pages)}]
    producer = {"kind": "deterministic", "tool": "specproof", "version": __version__}
    for artifact in (paths.sections_index, paths.sections_text):
        append_record(
            paths.manifest,
            ManifestRecord(
                artifact=paths.rel(artifact),
                sha256=sha256_file(artifact),
                stage="segment",
                producer=producer,
                inputs=inputs,
                created_at=_now(),
            ),
        )
    kinds: dict[str, int] = {}
    for section in sections:
        kinds[section.entry["kind"]] = kinds.get(section.entry["kind"], 0) + 1
    log.info("segment: %d sections %s", len(sections), dict(sorted(kinds.items())))


@app.command()
def verify(
    section: Annotated[list[str] | None, typer.Option("--section")] = None,
    chapter: Annotated[int | None, typer.Option("--chapter")] = None,
    all_: Annotated[bool, typer.Option("--all")] = True,
    report_only: Annotated[bool, typer.Option("--report-only")] = False,
) -> None:
    """Run deterministic verification rules V1-V5 on contract sections."""
    _stub("T05")


@app.command("loop-status")
def loop_status(json_: Annotated[bool, typer.Option("--json")] = False) -> None:
    """Show per-section loop state."""
    _stub("T06")


@app.command()
def classify() -> None:
    """Apply the classification state machine and write feedback."""
    _stub("T06")


@app.command("export-openapi")
def export_openapi() -> None:
    """Export verified sections to OpenAPI 3.1."""
    _stub("T09")


@app.command()
def compare(community: Annotated[bool, typer.Option("--community")] = False) -> None:
    """Diff the exported contract against the community OpenAPI."""
    _stub("T09")


@app.command()
def conform(client: Annotated[Path | None, typer.Option("--client")] = None) -> None:
    """Check client code against the verified contract."""
    _stub("T10")


@app.command()
def report() -> None:
    """Build the HTML, JSON and SARIF evidence pack."""
    _stub("T12")


@app.command("eval")
def eval_(thresholds: Path = Path("eval/thresholds.yaml")) -> None:
    """Compare metrics against the eval gate thresholds."""
    _stub("T11")


@app.command("audit-sample")
def audit_sample(n: int = 40, seed: int = 20260926) -> None:
    """Draw a stratified blind audit sample."""
    _stub("T11")


@app.command("audit-score")
def audit_score() -> None:
    """Join audit verdicts with statuses and compute audited metrics."""
    _stub("T11")


@app.command()
def guard(base: Annotated[str | None, typer.Option("--base")] = None) -> None:
    """Fail if protected paths changed since the task base commit."""
    _stub("T06")
