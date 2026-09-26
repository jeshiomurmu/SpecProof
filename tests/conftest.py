import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from specproof.ingest.extractors import Page, PdfplumberExtractor
from specproof.ingest.segment import Section, segment
from specproof.models.verification import VerificationResult
from specproof.verify.engine import verify_section
from specproof.verify.grounding import SectionContext

REPO_ROOT = Path(__file__).resolve().parent.parent
SPEC_PDF = REPO_ROOT / "artifacts" / "work" / "spec.pdf"
GOOD_DIR = Path(__file__).parent / "fixtures" / "contracts_good"


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if SPEC_PDF.exists():
        return
    skip = pytest.mark.skip(reason="run `make fetch` first")
    for item in items:
        if "real_source" in item.keywords:
            item.add_marker(skip)


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return REPO_ROOT


@pytest.fixture(scope="session")
def synthetic_pdf(tmp_path_factory: pytest.TempPathFactory) -> Path:
    from fixtures.build_synthetic_pdf import build

    return build(tmp_path_factory.mktemp("fx01") / "synthetic.pdf")


@pytest.fixture(scope="session")
def synthetic_pages(synthetic_pdf: Path) -> list[Page]:
    return PdfplumberExtractor().extract(synthetic_pdf)


@pytest.fixture(scope="session")
def synthetic_sections(synthetic_pages: list[Page]) -> dict[str, Section]:
    return {s.entry["section_id"]: s for s in segment(synthetic_pages)}


@pytest.fixture(scope="session")
def page_texts(synthetic_pages: list[Page]) -> dict[int, str]:
    return {p.number: p.text for p in synthetic_pages}


@pytest.fixture(name="good")
def good_contract() -> Callable[[str], dict[str, Any]]:
    """Return a fresh dict of an FX-02 golden contract."""

    def load(section_id: str) -> dict[str, Any]:
        data: dict[str, Any] = json.loads((GOOD_DIR / f"{section_id}.json").read_text("utf-8"))
        return data

    return load


@pytest.fixture(scope="session")
def section_ctx(
    synthetic_sections: dict[str, Section], page_texts: dict[int, str]
) -> Callable[[str], SectionContext]:
    def build(section_id: str) -> SectionContext:
        section = synthetic_sections[section_id]
        return SectionContext.build(page_texts, section.lines, section.entry)

    return build


@pytest.fixture
def workspace(synthetic_pdf: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A repo-shaped temp dir with the synthetic PDF ingested and segmented; cwd set to it."""
    import shutil

    from typer.testing import CliRunner

    from specproof.cli import app

    work = tmp_path / "artifacts" / "work"
    work.mkdir(parents=True)
    shutil.copyfile(synthetic_pdf, work / "spec.pdf")
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    assert runner.invoke(app, ["ingest"]).exit_code == 0
    assert runner.invoke(app, ["segment"]).exit_code == 0
    return tmp_path


@pytest.fixture(scope="session")
def run_verify(
    synthetic_sections: dict[str, Section], page_texts: dict[int, str]
) -> Callable[[dict[str, Any] | str, str], VerificationResult]:
    """Verify a contract (dict or raw JSON text) against the synthetic PDF."""

    def run(contract: dict[str, Any] | str, section_id: str) -> VerificationResult:
        raw = contract if isinstance(contract, str) else json.dumps(contract)
        section = synthetic_sections[section_id]
        return verify_section(raw, section.entry, page_texts, section.lines)

    return run
