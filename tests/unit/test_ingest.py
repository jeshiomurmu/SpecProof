import shutil
from pathlib import Path

import pytest
from typer.testing import CliRunner

from specproof.cli import app
from specproof.ingest.extractors import (
    Page,
    PdfplumberExtractor,
    PdftotextExtractor,
    select_extractor,
)
from specproof.util.hashing import sha256_file
from specproof.util.io_json import load_json
from specproof.util.io_pages import read_pages
from specproof.util.text import row_tokens


def _row_names(pages: list[str]) -> set[str]:
    return {tok[0] for text in pages for line in text.splitlines() if (tok := row_tokens(line))}


@pytest.mark.unit
def test_ING_001_page_count(synthetic_pdf: Path) -> None:
    assert len(select_extractor("auto").extract(synthetic_pdf)) == 7


@pytest.mark.unit
def test_ING_002_layout_fidelity(synthetic_pdf: Path) -> None:
    page4 = select_extractor("auto").extract(synthetic_pdf)[3]
    assert page4.number == 4
    rows = [row_tokens(line) for line in page4.text.splitlines()]
    assert ("color", "T", "String") in rows


@pytest.mark.unit
def test_ING_003_stable_hashes(synthetic_pdf: Path) -> None:
    first = [p.sha256 for p in select_extractor("auto").extract(synthetic_pdf)]
    second = [p.sha256 for p in select_extractor("auto").extract(synthetic_pdf)]
    assert first == second


@pytest.mark.unit
def test_ING_004_manifest_records_extractor_and_input(
    synthetic_pdf: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    work = tmp_path / "artifacts" / "work"
    work.mkdir(parents=True)
    shutil.copyfile(synthetic_pdf, work / "spec.pdf")
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(app, ["ingest"])
    assert result.exit_code == 0, result.output
    records = load_json(tmp_path / "artifacts" / "manifest.json")
    ingest = [r for r in records if r["stage"] == "ingest"]
    assert len(ingest) == 1
    record = ingest[0]
    assert record["artifact"] == "artifacts/work/pages.jsonl"
    assert record["sha256"] == sha256_file(work / "pages.jsonl")
    assert record["producer"]["extractor"] == "pdfplumber"
    assert record["producer"]["extractor_version"]
    assert record["inputs"][0]["sha256"] == sha256_file(synthetic_pdf)


@pytest.mark.unit
@pytest.mark.parametrize("found", ["/usr/bin/pdftotext", None], ids=["installed", "missing"])
def test_ING_005_auto_picks_pdfplumber(monkeypatch: pytest.MonkeyPatch, found: str | None) -> None:
    monkeypatch.setattr(shutil, "which", lambda _name: found)
    assert isinstance(select_extractor("auto"), PdfplumberExtractor)


@pytest.mark.unit
def test_ING_005_explicit_pdftotext(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(shutil, "which", lambda _name: "/usr/bin/pdftotext")
    assert isinstance(select_extractor("pdftotext"), PdftotextExtractor)
    monkeypatch.setattr(shutil, "which", lambda _name: None)
    with pytest.raises(RuntimeError, match="pdftotext"):
        select_extractor("pdftotext")


FX01_ROWS = {
    4: {"Authorization", "name", "color", "size"},
    6: {"id", "name", "color", "size", "created_at"},
    7: {"ids"},
}


def _rows_by_page(pages: list[Page]) -> dict[int, set[str]]:
    found = {p.number: _row_names([p.text]) for p in pages}
    return {n: rows for n, rows in found.items() if rows}


@pytest.mark.unit
def test_ING_006_default_extractor_fidelity(synthetic_pdf: Path) -> None:
    assert _rows_by_page(select_extractor("auto").extract(synthetic_pdf)) == FX01_ROWS


@pytest.mark.unit
@pytest.mark.skipif(shutil.which("pdftotext") is None, reason="pdftotext not installed")
@pytest.mark.xfail(
    strict=False, reason="pdftotext -layout splits table columns; see review/SPIKE_T02.md"
)
def test_ING_006_pdftotext_fidelity_known_defect(synthetic_pdf: Path) -> None:
    assert _rows_by_page(PdftotextExtractor().extract(synthetic_pdf)) == FX01_ROWS


@pytest.mark.unit
def test_ING_007_cache_and_roundtrip(
    synthetic_pdf: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    work = tmp_path / "artifacts" / "work"
    work.mkdir(parents=True)
    shutil.copyfile(synthetic_pdf, work / "spec.pdf")
    monkeypatch.chdir(tmp_path)
    assert CliRunner().invoke(app, ["ingest"]).exit_code == 0
    written = read_pages(work / "pages.jsonl")
    assert [p.number for p in written] == list(range(1, 8))
    assert written == PdfplumberExtractor().extract(synthetic_pdf)

    def boom(self: PdfplumberExtractor, pdf: Path) -> list[Page]:
        raise AssertionError("cache miss: extracted again")

    monkeypatch.setattr(PdfplumberExtractor, "extract", boom)
    assert CliRunner().invoke(app, ["ingest"]).exit_code == 0


@pytest.mark.unit
def test_ING_008_common_left_margin_removed() -> None:
    from specproof.ingest.extractors import make_page

    page = make_page(1, "\n        2.2 Title   \n          indented\n\n        body\n\n")
    assert page.text == "\n2.2 Title\n  indented\n\nbody"


@pytest.mark.unit
def test_CLI_002_ingest_without_pdf_exits_2(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    assert CliRunner().invoke(app, ["ingest"]).exit_code == 2
