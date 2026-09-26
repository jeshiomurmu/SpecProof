from collections.abc import Callable
from types import SimpleNamespace
from typing import Any

import pytest
from fixtures.mutations import mutate

from specproof.models.contract import Citation, ContractSection, FieldSpec
from specproof.verify import grounding
from specproof.verify.grounding import (
    SectionContext,
    check_citation,
    check_enum,
    check_name_in_quote,
    check_row,
    check_sample_verbatim,
)

Ctx = Callable[[str], SectionContext]
Good = Callable[[str], dict[str, Any]]


def _field(good: Good, name: str, **changes: Any) -> FieldSpec:
    data = next(f for f in good("S-2.2")["fields"] if f["name"] == name)
    data.update(changes)
    return FieldSpec.model_validate(data)


def _codes(issues: list[Any]) -> list[str]:
    return [i.code for i in issues]


@pytest.mark.unit
def test_VER_001_exact_quote_passes(section_ctx: Ctx) -> None:
    issues, grounded = check_citation(
        section_ctx("S-2.2"), Citation(page=4, quote="Request URL: /api/v1/widgets")
    )
    assert (issues, grounded) == ([], True)


@pytest.mark.unit
def test_VER_002_whitespace_variant_passes(section_ctx: Ctx) -> None:
    issues, grounded = check_citation(
        section_ctx("S-2.2"), Citation(page=4, quote="Request   URL:\n  /api/v1/widgets")
    )
    assert (issues, grounded) == ([], True)


@pytest.mark.unit
def test_VER_003_short_quote(section_ctx: Ctx) -> None:
    short = Citation.model_construct(page=4, quote="Method: GET")
    issues, grounded = check_citation(section_ctx("S-2.2"), short)
    assert _codes(issues) == ["V2_QUOTE_TOO_SHORT"]
    assert grounded is False


@pytest.mark.unit
def test_VER_004_fabricated_quote_fails(section_ctx: Ctx) -> None:
    issues, grounded = check_citation(
        section_ctx("S-2.2"), Citation(page=4, quote="Request URL: /api/v1/gizmos")
    )
    assert _codes(issues) == ["V2_CITATION_NOT_FOUND"]
    assert grounded is False
    hint = issues[0].hint
    assert hint is not None and hint["closest_page"] == 4
    assert "Request URL: /api/v1/widgets" in str(hint["closest_match"])


@pytest.mark.unit
def test_VER_005_wrong_page_suggests_true_page(section_ctx: Ctx) -> None:
    issues, grounded = check_citation(
        section_ctx("S-2.2"), Citation(page=5, quote="Request URL: /api/v1/widgets")
    )
    assert _codes(issues) == ["V2_CITATION_WRONG_PAGE"]
    assert issues[0].hint == {"suggested_page": 4}
    assert grounded is False


@pytest.mark.unit
def test_VER_006_name_not_in_quote(good: Good) -> None:
    field = _field(good, "name", citation={"page": 4, "quote": "Permission Key: edit:widget"})
    assert _codes(check_name_in_quote(field)) == ["V2_NAME_NOT_IN_QUOTE"]
    assert check_name_in_quote(_field(good, "name")) == []


@pytest.mark.unit
def test_VER_007_required_flipped(section_ctx: Ctx, good: Good) -> None:
    issues, found = check_row(section_ctx("S-2.2"), _field(good, "name", required=False))
    assert _codes(issues) == ["V2_ROW_MISMATCH"]
    assert found is True
    assert issues[0].evidence is not None and issues[0].evidence.page == 4


@pytest.mark.unit
def test_VER_008_type_flipped(section_ctx: Ctx, good: Good) -> None:
    field = _field(good, "name", type="integer", type_raw="Integer")
    issues, _found = check_row(section_ctx("S-2.2"), field)
    assert _codes(issues) == ["V2_ROW_MISMATCH"]


@pytest.mark.unit
def test_VER_009_wrapped_row_is_info_only(section_ctx: Ctx, good: Good) -> None:
    issues, found = check_row(section_ctx("S-2.2"), _field(good, "notes"))
    assert _codes(issues) == ["V2_ROW_NOT_FOUND"]
    assert (issues[0].severity, issues[0].category) == ("info", "info")
    assert found is False


@pytest.mark.unit
def test_VER_010_enum_not_grounded(good: Good) -> None:
    field = _field(good, "color", enum=["Red", "Green", "Blue", "Purple"])
    issues = check_enum(field)
    assert _codes(issues) == ["V2_ENUM_NOT_GROUNDED"]
    assert "Purple" in issues[0].message


@pytest.mark.unit
def test_VER_011_enum_grounded_via_schema_page(section_ctx: Ctx, good: Good) -> None:
    field = _field(good, "color")
    assert check_enum(field) == []
    assert field.enum_citation is not None
    assert check_citation(section_ctx("S-2.2"), field.enum_citation) == ([], True)


@pytest.mark.unit
@pytest.mark.parametrize("score", [100.0, 0.0])
def test_VER_012_fuzzy_never_decides(
    section_ctx: Ctx, monkeypatch: pytest.MonkeyPatch, score: float
) -> None:
    ctx = section_ctx("S-2.2")
    good_cite = Citation(page=4, quote="Request URL: /api/v1/widgets")
    bad_cite = Citation(page=4, quote="Request URL: /api/v1/gizmos")
    before = (check_citation(ctx, good_cite)[1], _codes(check_citation(ctx, bad_cite)[0]))

    fake = SimpleNamespace(
        partial_ratio_alignment=lambda *a, **k: SimpleNamespace(
            score=score, dest_start=0, dest_end=5
        )
    )
    monkeypatch.setattr(grounding, "fuzz", fake)
    after = (check_citation(ctx, good_cite)[1], _codes(check_citation(ctx, bad_cite)[0]))
    assert before == after == (True, ["V2_CITATION_NOT_FOUND"])


@pytest.mark.unit
def test_VER_013_repaired_sample_not_verbatim(section_ctx: Ctx, good: Good) -> None:
    ctx = section_ctx("S-2.2")
    original = ContractSection.model_validate(good("S-2.2"))
    repaired = ContractSection.model_validate(mutate(good("S-2.2"), "repair_sample"))
    assert original.samples.request is not None and repaired.samples.request is not None
    assert check_sample_verbatim(ctx, original.samples.request, "request") == []
    issues = check_sample_verbatim(ctx, repaired.samples.request, "request")
    assert _codes(issues) == ["V2_SAMPLE_NOT_VERBATIM"]
    assert issues[0].hint is not None and "Green" in str(issues[0].hint["first_unmatched"])
