from __future__ import annotations

from pathlib import Path

import pytest
import pypdf
from click.testing import CliRunner

from src.extract_pages import main


def test_cli_happy_path_creates_output(pdf_factory, tmp_path: Path, monkeypatch):
    # Готовим структуру "проекта"
    input_dir = tmp_path / "input_pdfs"
    output_dir = tmp_path / "output_pdfs"
    input_dir.mkdir()
    output_dir.mkdir()

    # Создаём входной pdf именно в input_pdfs
    src_pdf = input_dir / "report.pdf"
    # pdf_factory создаёт в tmp_path, поэтому создадим вручную в input_dir:
    from tests.conftest import make_pdf
    make_pdf(src_pdf, pages=10)

    monkeypatch.chdir(tmp_path)

    runner = CliRunner()
    result = runner.invoke(main, ["--input", "report.pdf", "--pages", "2-4", "--output", "sel.pdf"])
    assert result.exit_code == 0, result.output
    assert "Создан файл:" in result.output

    out_pdf = output_dir / "sel.pdf"
    assert out_pdf.exists()

    reader = pypdf.PdfReader(str(out_pdf))
    assert len(reader.pages) == 3


def test_cli_rejects_non_pdf_extension(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(main, ["--input", "file.txt", "--pages", "1"])
    assert result.exit_code != 0
    assert "расширение .pdf" in result.output


def test_cli_rejects_missing_file(tmp_path: Path, monkeypatch):
    (tmp_path / "input_pdfs").mkdir()
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(main, ["--input", "missing.pdf", "--pages", "1"])
    assert result.exit_code != 0
    assert "Файл не найден" in result.output


def test_cli_rejects_bad_pages_spec(tmp_path: Path, monkeypatch):
    input_dir = tmp_path / "input_pdfs"
    input_dir.mkdir()
    from tests.conftest import make_pdf
    make_pdf(input_dir / "a.pdf", pages=3)

    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(main, ["--input", "a.pdf", "--pages", "3-2"])
    assert result.exit_code != 0
    assert "--pages" in result.output  # click покажет, где ошибка
