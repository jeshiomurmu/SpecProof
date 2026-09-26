import json
from pathlib import Path

import pytest

from specproof.ingest.extractors import Page, make_page
from specproof.ingest.segment import normalize_path_hint, segment

EXPECTED_IDS = ["S-1.1", "S-2.1", "S-2.2", "S-2.3", "S-2.4"]


def _by_id(pages: list[Page]) -> dict[str, dict[str, object]]:
    return {s.entry["section_id"]: s.entry for s in segment(pages)}  # type: ignore[misc]


@pytest.mark.unit
def test_SEG_001_toc_skipped(synthetic_pages: list[Page]) -> None:
    sections = _by_id(synthetic_pages)
    assert all(entry["page_start"] != 1 for entry in sections.values())
    assert sections["S-1.1"]["page_start"] == 2


@pytest.mark.unit
def test_SEG_002_heading_detection(synthetic_pages: list[Page]) -> None:
    assert [s.entry["section_id"] for s in segment(synthetic_pages)] == EXPECTED_IDS


@pytest.mark.unit
def test_SEG_003_endpoint_kind(synthetic_pages: list[Page]) -> None:
    sections = _by_id(synthetic_pages)
    assert sections["S-2.2"]["kind"] == "endpoint"
    assert sections["S-2.4"]["kind"] == "endpoint"


@pytest.mark.unit
def test_SEG_004_schema_and_overview_kind(synthetic_pages: list[Page]) -> None:
    sections = _by_id(synthetic_pages)
    assert sections["S-2.1"]["kind"] == "schema"
    assert sections["S-1.1"]["kind"] == "overview"


@pytest.mark.unit
def test_SEG_005_page_span(synthetic_pages: list[Page]) -> None:
    s22 = _by_id(synthetic_pages)["S-2.2"]
    assert (s22["page_start"], s22["page_end"]) == (4, 5)


@pytest.mark.unit
def test_SEG_006_hints(synthetic_pages: list[Page]) -> None:
    sections = _by_id(synthetic_pages)
    assert (sections["S-2.2"]["method_hint"], sections["S-2.2"]["path_hint"]) == (
        "POST",
        "/api/v1/widgets",
    )
    assert (sections["S-2.3"]["method_hint"], sections["S-2.3"]["path_hint"]) == (
        "GET",
        "/api/v1/widgets/:id",
    )
    assert sections["S-2.4"]["method_hint"] == "DELETE"
    assert sections["S-2.1"]["method_hint"] is None
    assert sections["S-2.1"]["path_hint"] is None


@pytest.mark.unit
def test_SEG_007_order_and_stable_ids(synthetic_pages: list[Page]) -> None:
    first = [s.entry for s in segment(synthetic_pages)]
    second = [s.entry for s in segment(synthetic_pages)]
    assert first == second
    keys = [(e["chapter"], int(str(e["number"]).split(".")[1])) for e in first]
    assert keys == sorted(keys)


@pytest.mark.unit
def test_SEG_007_monotonic_filter_rejects_stray_and_version_strings() -> None:
    pages = [
        make_page(1, "1.1 Intro\nRequires 1.22.16 or later"),
        make_page(2, "2.1 Users\nRequest URL: /api/v1/users\n    1.5 Stray Value In Table"),
        make_page(3, "2.2 Groups\ntext"),
    ]
    assert [s.entry["section_id"] for s in segment(pages)] == ["S-1.1", "S-2.1", "S-2.2"]


@pytest.mark.unit
def test_SEG_011_wide_layout_spacing_and_marker_spacing() -> None:
    spaced = "3.20" + " " * 9 + (" " * 12).join(["Fetch", "the", "Access", "Policies", "Assigned"])
    assert len(spaced) > 80
    pages = [
        make_page(1, "3.1 Schemas\ntext"),
        make_page(2, spaced + "\nRequest   URL:   /api/v1/policies\nMethod :  GET"),
    ]
    sections = {s.entry["section_id"]: s.entry for s in segment(pages)}
    assert sections["S-3.20"]["title"] == "Fetch the Access Policies Assigned"
    assert sections["S-3.20"]["kind"] == "endpoint"
    assert (sections["S-3.20"]["method_hint"], sections["S-3.20"]["path_hint"]) == (
        "GET",
        "/api/v1/policies",
    )


@pytest.mark.unit
def test_SEG_008_no_full_text_in_index(synthetic_pages: list[Page]) -> None:
    for section in segment(synthetic_pages):
        assert set(section.entry) == {
            "section_id",
            "chapter",
            "number",
            "title",
            "kind",
            "page_start",
            "page_end",
            "method_hint",
            "path_hint",
            "text_sha256",
        }
        for value in section.entry.values():
            assert len(json.dumps(value)) <= 200


@pytest.mark.unit
@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("/api/v1/users", "/api/v1/users"),
        ("api/v1/users/", "/api/v1/users"),
        ("/api/v1/users?page=1", "/api/v1/users"),
        ("/api/v1/users/:id", "/api/v1/users/:id"),
        ("Your", None),
    ],
)
def test_SEG_009_path_hint_normalization(raw: str, expected: str | None) -> None:
    assert normalize_path_hint(raw) == expected


@pytest.mark.unit
def test_SEG_010_segment_cli_writes_index_and_manifest(
    synthetic_pdf: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import shutil

    from typer.testing import CliRunner

    from specproof.cli import app
    from specproof.util.io_json import load_json

    work = tmp_path / "artifacts" / "work"
    work.mkdir(parents=True)
    shutil.copyfile(synthetic_pdf, work / "spec.pdf")
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    assert runner.invoke(app, ["ingest"]).exit_code == 0
    assert runner.invoke(app, ["segment"]).exit_code == 0
    index = load_json(tmp_path / "artifacts" / "sections_index.json")
    assert [e["section_id"] for e in index] == EXPECTED_IDS
    manifest = load_json(tmp_path / "artifacts" / "manifest.json")
    assert {r["stage"] for r in manifest} == {"ingest", "segment"}
    before = (tmp_path / "artifacts" / "manifest.json").read_bytes()
    assert runner.invoke(app, ["segment"]).exit_code == 0
    assert (tmp_path / "artifacts" / "manifest.json").read_bytes() == before
