from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4


def make_pdf(path: Path, pages: int, title_prefix: str = "Page") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(path), pagesize=A4)
    for i in range(1, pages + 1):
        c.setFont("Helvetica", 18)
        c.drawString(72, 800, f"{title_prefix} {i}")
        c.showPage()
    c.save()


@pytest.fixture()
def pdf_factory(tmp_path: Path):
    def _factory(name: str, pages: int) -> Path:
        pdf_path = tmp_path / name
        make_pdf(pdf_path, pages=pages)
        return pdf_path
    return _factory

