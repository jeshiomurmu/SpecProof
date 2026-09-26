"""FX-03: single-defect mutations of the FX-02 S-2.2 contract, each with its expected code."""

import copy
from typing import Any

EXPECTED_CODE = {
    "fabricate_quote": "V2_CITATION_NOT_FOUND",
    "wrong_page": "V2_CITATION_WRONG_PAGE",
    "flip_required": "V2_ROW_MISMATCH",
    "flip_type": "V2_ROW_MISMATCH",
    "drop_field": "V5_COVERAGE_GAP",
    "enum_not_grounded": "V2_ENUM_NOT_GROUNDED",
    "repair_sample": "V2_SAMPLE_NOT_VERBATIM",
    "wrong_path": "V4_PATH_MISMATCH",
    "wrong_method": "V4_METHOD_MISMATCH",
    # The Citation validator rejects < 12 chars at load time, so a file with a short quote
    # fails V1; V2_QUOTE_TOO_SHORT stays as defense in depth and is covered by VER-003.
    "short_quote": "V1_SCHEMA_INVALID",
    "name_not_in_quote": "V2_NAME_NOT_IN_QUOTE",
}


def _field(contract: dict[str, Any], name: str) -> dict[str, Any]:
    return next(f for f in contract["fields"] if f["name"] == name)


def mutate(contract: dict[str, Any], kind: str) -> dict[str, Any]:
    """Return a deep copy of the S-2.2 contract with exactly one planted defect."""
    out = copy.deepcopy(contract)
    if kind == "fabricate_quote":
        _field(out, "size")["citation"]["quote"] = "size   F   Integer   Size in inches."
    elif kind == "wrong_page":
        _field(out, "name")["citation"]["page"] = 5
    elif kind == "flip_required":
        _field(out, "name")["required"] = False
    elif kind == "flip_type":
        _field(out, "size").update(type="string", type_raw="String")
    elif kind == "drop_field":
        out["fields"] = [f for f in out["fields"] if f["name"] != "size"]
    elif kind == "enum_not_grounded":
        _field(out, "color")["enum"].append("Purple")
    elif kind == "repair_sample":
        request = out["samples"]["request"]
        request["raw"] = request["raw"].replace("Grean", "Green")
    elif kind == "wrong_path":
        out["path"] = "/api/v1/gizmos"
    elif kind == "wrong_method":
        out["method"] = "PUT"
    elif kind == "short_quote":
        _field(out, "size")["citation"]["quote"] = "size F"
    elif kind == "name_not_in_quote":
        _field(out, "name")["citation"] = {"page": 4, "quote": "Permission Key: edit:widget"}
    else:
        raise ValueError(f"unknown mutation {kind!r}")
    return out
