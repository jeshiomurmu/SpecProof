"""Reading and writing artifacts/work/pages.jsonl."""

import json
from pathlib import Path

from specproof.ingest.extractors import Page
from specproof.util.io_json import write_bytes_atomic


def write_pages(path: Path, pages: list[Page]) -> None:
    """Write one sorted-key JSON object per page, ordered by page number, LF endings."""
    lines = [
        json.dumps(
            {"number": p.number, "sha256": p.sha256, "text": p.text},
            sort_keys=True,
            ensure_ascii=False,
        )
        for p in sorted(pages, key=lambda p: p.number)
    ]
    write_bytes_atomic(path, ("\n".join(lines) + "\n").encode("utf-8"))


def read_pages(path: Path) -> list[Page]:
    """Read pages.jsonl back into Page objects."""
    pages = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line:
            row = json.loads(line)
            pages.append(Page(number=row["number"], text=row["text"], sha256=row["sha256"]))
    return pages
