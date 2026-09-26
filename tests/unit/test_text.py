import pytest
from hypothesis import given
from hypothesis import strategies as st

from specproof.util.text import norm, row_tokens

NBSP = chr(0x00A0)
FULLWIDTH_FIRST = "".join(chr(0xFEE0 + ord(c)) for c in "first")
LDQ, RDQ, LSQ, RSQ = chr(0x201C), chr(0x201D), chr(0x2018), chr(0x2019)


@pytest.mark.unit
def test_TXT_001_nfkc_normalization() -> None:
    assert norm(FULLWIDTH_FIRST) == "first"


@pytest.mark.unit
def test_TXT_002_whitespace_collapse() -> None:
    assert norm("a \n\t  b") == "a b"
    assert norm(f"{NBSP} a{NBSP}{NBSP}b \n") == "a b"


@pytest.mark.unit
def test_TXT_003_smart_quotes() -> None:
    assert norm(f"{LDQ}x{RDQ}") == '"x"'
    assert norm(f"{LSQ}y{RSQ}") == "'y'"


@pytest.mark.unit
@given(st.text())
def test_TXT_004_norm_is_idempotent(s: str) -> None:
    assert norm(norm(s)) == norm(s)


@pytest.mark.unit
def test_TXT_005_row_tokens() -> None:
    assert row_tokens("  first_name   T   String   First") == ("first_name", "T", "String")
    assert row_tokens("ids  T  Array[String]  x") == ("ids", "T", "Array[String]")


@pytest.mark.unit
def test_TXT_006_prose_rejected() -> None:
    assert row_tokens("the first_name T is String") is None
