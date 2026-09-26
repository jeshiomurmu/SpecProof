from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SPEC_PDF = REPO_ROOT / "artifacts" / "work" / "spec.pdf"


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if SPEC_PDF.exists():
        return
    skip = pytest.mark.skip(reason="run `make fetch` first")
    for item in items:
        if "real_source" in item.keywords:
            item.add_marker(skip)


@pytest.fixture
def repo_root() -> Path:
    return REPO_ROOT
