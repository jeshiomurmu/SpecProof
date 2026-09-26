"""Throwaway T02 spike: compare pdftotext -layout vs pdfplumber layout=True on 3 pages."""

import re
import subprocess
import sys

import pdfplumber

PDF = "artifacts/work/spec.pdf"
ROW = re.compile(r"^\s*first_name\s{2,}T\s{2,}String")
ENUM = "enum reason {Interview,Business,Cooperation,Others}"


def via_pdftotext(n: int) -> str:
    cmd = ["pdftotext", "-layout", "-enc", "UTF-8", "-f", str(n), "-l", str(n), PDF, "-"]
    return subprocess.run(cmd, check=True, capture_output=True).stdout.decode("utf-8")


def via_pdfplumber(n: int) -> str:
    with pdfplumber.open(PDF) as pdf:
        return pdf.pages[n - 1].extract_text(layout=True) or ""


def evidence(text: str, pred: object) -> str:
    for line in text.splitlines():
        if pred(line):  # type: ignore[operator]
            return line.rstrip()
    return "(none)"


for name, fn in [("pdftotext", via_pdftotext), ("pdfplumber", via_pdfplumber)]:
    p14, p52, p56 = fn(14), fn(52), fn(56)
    sys.stdout.buffer.write(
        (
            f"## {name}\n"
            f"p14 row match: {bool(evidence(p14, ROW.match) != '(none)')}\n"
            f"  line: {evidence(p14, ROW.match)!r}\n"
            f"p52 enum present: {ENUM in p52}\n"
            f"  line: {evidence(p52, lambda s: 'enum reason' in s)!r}\n"
            f"p56 Interviemw present: {'Interviemw' in p56}\n"
            f"  line: {evidence(p56, lambda s: 'Interviemw' in s)!r}\n"
        ).encode()
    )
