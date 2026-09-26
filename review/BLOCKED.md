# BLOCKED log

## RESOLVED 2026-09-26: T02, test ING-006 (extractor parity)

**Problem:** ING-006 required that both extractors detect the same row names on FX-01. xpdf `pdftotext -layout` (4.00) splits the Parameter column into a separate text block, so its rows never sit on single lines. This is the same defect the spike found on the real PDF, p52 (`review/SPIKE_T02.md`). No code change can make xpdf's output match.

**Resolution (option 1, taken by Claude Code; the human asked to continue without choosing):** ING-006 is now a fidelity test. The default extractor must detect exactly the expected row names on each page of FX-01, a stronger check than parity. A second test runs the same assertion on pdftotext as `xfail(strict=False)`, which documents the known defect. The TEST_PLAN row was updated.
