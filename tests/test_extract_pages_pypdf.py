from __future__ import annotations

from pathlib import Path

import pytest
import pypdf

from src.extract_pages import extract_pages_pypdf


def test_extract_pages_creates_pdf_with_expected_page_count(pdf_factory, tmp_path: Path):
    src_pdf = pdf_factory("source.pdf", pages=6)
    out_pdf = tmp_path / "out" / "selection.pdf"

    extract_pages_pypdf(str(src_pdf), str(out_pdf), page_numbers=[2, 4, 6])

    reader = pypdf.PdfReader(str(out_pdf))
    assert len(reader.pages) == 3


def test_extract_pages_uses_1_based_indexing(pdf_factory, tmp_path: Path):
    src_pdf = pdf_factory("source.pdf", pages=3)
    out_pdf = tmp_path / "out" / "one.pdf"

    # Берём "1" => должна быть 1 страница, ошибок быть не должно
    extract_pages_pypdf(str(src_pdf), str(out_pdf), page_numbers=[1])

    reader = pypdf.PdfReader(str(out_pdf))
    assert len(reader.pages) == 1


def test_extract_pages_raises_on_encrypted_pdf(pdf_factory, tmp_path: Path):
    src_plain = pdf_factory("plain.pdf", pages=2)
    encrypted_path = tmp_path / "encrypted.pdf"

    # Создаём зашифрованную копию
    r = pypdf.PdfReader(str(src_plain))
    w = pypdf.PdfWriter()
    for page in r.pages:
        w.add_page(page)
    w.encrypt("pass")

    with open(encrypted_path, "wb") as f:
        w.write(f)

    out_pdf = tmp_path / "out" / "x.pdf"
    with pytest.raises(RuntimeError) as e:
        extract_pages_pypdf(str(encrypted_path), str(out_pdf), page_numbers=[1])
    assert "Зашифрованные PDF" in str(e.value)
