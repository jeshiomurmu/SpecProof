"""SpecProof command-line interface (architecture section 10)."""

import logging
from pathlib import Path
from typing import Annotated

import typer

app = typer.Typer(help="SpecProof: verified, cited contracts from document-only API specs.")
log = logging.getLogger("specproof")


def _stub(task: str) -> None:
    log.warning("not implemented (%s)", task)


@app.callback()
def main(verbose: Annotated[bool, typer.Option("--verbose", "-v")] = False) -> None:
    """Configure logging for every command."""
    logging.basicConfig(level=logging.DEBUG if verbose else logging.INFO, format="%(message)s")


@app.command()
def fetch(lock: Path = Path("sources/sources.lock.yaml")) -> None:
    """Download pinned sources and verify their SHA-256."""
    _stub("T02")


@app.command()
def ingest(extractor: str = "auto") -> None:
    """Extract page text from the spec PDF into artifacts/work/pages.jsonl."""
    _stub("T02")


@app.command()
def segment() -> None:
    """Split pages into sections and write artifacts/sections_index.json."""
    _stub("T03")


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
