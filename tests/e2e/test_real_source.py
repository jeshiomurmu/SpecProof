from pathlib import Path

import pytest

from specproof.config import Paths
from specproof.ingest.extractors import Page, select_extractor
from specproof.models.manifest import find_record
from specproof.util.hashing import sha256_file
from specproof.util.io_pages import read_pages
from specproof.util.text import row_tokens

PIN = "d204c8b9ad4d329f6c89e71ebb5ccf446bcc30d2668673011bbe99a909a6a534"


@pytest.fixture(scope="module")
def real_pages(repo_root: Path) -> list[Page]:
    """Use the pipeline's pages.jsonl when the manifest ties it to the pinned PDF, else extract."""
    paths = Paths.from_root(repo_root)
    record = find_record(paths.manifest, paths.rel(paths.pages))
    if (
        record is not None
        and paths.pages.exists()
        and record.producer.get("extractor") == "pdfplumber"
        and record.inputs[0]["sha256"] == PIN
        and record.sha256 == sha256_file(paths.pages)
    ):
        return read_pages(paths.pages)
    return select_extractor("auto").extract(paths.spec_pdf)


@pytest.mark.real_source
def test_ING_R01_page_14_first_name_row(real_pages: list[Page]) -> None:
    page14 = real_pages[13]
    assert page14.number == 14
    rows = [row_tokens(line) for line in page14.text.splitlines()]
    assert ("first_name", "T", "String") in rows


@pytest.mark.real_source
def test_ING_R02_page_count_and_pin(real_pages: list[Page], repo_root: Path) -> None:
    assert len(real_pages) == 194
    assert sha256_file(repo_root / "artifacts" / "work" / "spec.pdf") == PIN
