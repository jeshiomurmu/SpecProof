"""FX-01 builder: draws synthetic_spec.yaml into a byte-reproducible PDF with reportlab."""

from pathlib import Path

import yaml
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

SPEC = Path(__file__).with_name("synthetic_spec.yaml")
FIVE_COLS = (72.0, 230.0, 290.0, 360.0, 480.0)
THREE_COLS = (72.0, 230.0, 360.0)
LEFT = 72.0
TOP = 800.0
LEADING = 13.0
FONT = ("Helvetica", 9)


def _draw_line(pdf: canvas.Canvas, line: str, y: float) -> None:
    if line.startswith("|"):
        cells = [c.strip() for c in line[1:].split("|")]
        cols = FIVE_COLS if len(cells) >= 4 else THREE_COLS
        for x, cell in zip(cols, cells, strict=False):
            if cell:
                pdf.drawString(x, y, cell)
        return
    indent = len(line) - len(line.lstrip(" "))
    if line.strip():
        pdf.drawString(LEFT + 5.0 * indent, y, line.strip())


def build(dest: Path, spec: Path = SPEC) -> Path:
    """Render the synthetic spec to dest; the same input always yields identical bytes."""
    data = yaml.safe_load(spec.read_text(encoding="utf-8"))
    pdf = canvas.Canvas(str(dest), pagesize=A4, invariant=1)
    for number, lines in enumerate(data["pages"], start=1):
        pdf.setFont(*FONT)
        y = TOP
        for line in lines:
            _draw_line(pdf, line, y)
            y -= LEADING
        pdf.drawString(LEFT, 30.0, f"{data['footer']}   {number}")
        pdf.showPage()
    pdf.save()
    return dest
