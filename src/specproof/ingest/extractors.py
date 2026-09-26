"""PDF page-text extractors. pdfplumber is the default; see review/SPIKE_T02.md."""

import shutil
import subprocess
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import pdfplumber

from specproof.util.hashing import sha256_text

_PARALLEL_MIN_PAGES = 24
_WORKERS = 8


@dataclass(frozen=True)
class Page:
    """One PDF page: 1-based number, cleaned layout text, sha256 of that text."""

    number: int
    text: str
    sha256: str


def make_page(number: int, raw: str) -> Page:
    """Build a Page with trailing spaces and trailing blank lines removed."""
    lines = [line.rstrip() for line in raw.replace("\r\n", "\n").split("\n")]
    while lines and not lines[-1]:
        lines.pop()
    text = "\n".join(lines)
    return Page(number=number, text=text, sha256=sha256_text(text))


class TextExtractor(Protocol):
    """Turns a PDF into per-page text."""

    name: str

    def version(self) -> str: ...

    def extract(self, pdf: Path) -> list[Page]: ...


def _plumber_pages(pdf: Path, numbers: list[int]) -> list[tuple[int, str]]:
    with pdfplumber.open(pdf) as doc:
        return [(n, doc.pages[n - 1].extract_text(layout=True) or "") for n in numbers]


class PdfplumberExtractor:
    """pdfplumber layout=True, split over worker processes for large documents."""

    name = "pdfplumber"

    def __init__(self, workers: int = _WORKERS) -> None:
        self.workers = workers

    def version(self) -> str:
        """Return the pdfplumber package version."""
        return str(pdfplumber.__version__)

    def extract(self, pdf: Path) -> list[Page]:
        """Extract every page, ordered by page number."""
        with pdfplumber.open(pdf) as doc:
            count = len(doc.pages)
        numbers = list(range(1, count + 1))
        if count < _PARALLEL_MIN_PAGES or self.workers <= 1:
            raw = _plumber_pages(pdf, numbers)
        else:
            chunks = [numbers[i :: self.workers] for i in range(self.workers)]
            with ProcessPoolExecutor(self.workers) as pool:
                parts = pool.map(_plumber_pages, [pdf] * len(chunks), chunks)
                raw = [item for part in parts for item in part]
        return [make_page(n, text) for n, text in sorted(raw)]


class PdftotextExtractor:
    """`pdftotext -layout` subprocess (xpdf or poppler; output differs between them)."""

    name = "pdftotext"

    def version(self) -> str:
        """Return the first line of `pdftotext -v`."""
        done = subprocess.run(["pdftotext", "-v"], capture_output=True, text=True)
        return (done.stderr or done.stdout).splitlines()[0].strip()

    def extract(self, pdf: Path) -> list[Page]:
        """Extract every page in one pass, split on form feeds."""
        cmd = ["pdftotext", "-layout", "-enc", "UTF-8", str(pdf), "-"]
        out = subprocess.run(cmd, check=True, capture_output=True).stdout.decode("utf-8")
        chunks = out.split("\f")
        if chunks and not chunks[-1].strip():
            chunks.pop()
        return [make_page(i, text) for i, text in enumerate(chunks, start=1)]


def select_extractor(name: str) -> TextExtractor:
    """Return the extractor for name; `auto` is pdfplumber per the T02 spike."""
    if name in ("auto", "pdfplumber"):
        return PdfplumberExtractor()
    if name == "pdftotext":
        if shutil.which("pdftotext") is None:
            raise RuntimeError("pdftotext requested but not found on PATH")
        return PdftotextExtractor()
    raise ValueError(f"unknown extractor {name!r}")
