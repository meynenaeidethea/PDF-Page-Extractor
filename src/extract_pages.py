"""Командная утилита и набор функций для извлечения страниц из PDF.

Модуль реализует:

* ``parse_page_spec`` — разбор строки с диапазонами страниц в упорядоченный
  список уникальных номеров.
* ``extract_pages_pypdf`` — извлечение заданных страниц с помощью
  библиотеки :mod:`pypdf`.
  
* CLI‑команду ``main`` на базе :mod:`click` для удобного использования
  из командной строки.

И функции, и командный интерфейс гарантируют проверку корректности
входных данных: существование файла, расширение, наличие страниц,
отсутствие шифрования и корректность диапазонов.
"""

from __future__ import annotations

import os
import re
from typing import Iterable, List, Optional, Sequence

import click

try:
    import pypdf  # type: ignore
except ImportError:  # pragma: no cover
    # В старых версиях пакет назывался PyPDF2; оставляем для совместимости
    import PyPDF2 as pypdf  # type: ignore

# Компилируем регулярные выражения один раз для повышения производительности
_RANGE_RE = re.compile(r"^(\d+)-(\d+)$")
_SINGLE_RE = re.compile(r"^\d+$")


def parse_page_spec(page_spec: str, total_pages: Optional[int] = None) -> List[int]:
    """Разобрать строку с диапазонами в список уникальных номеров страниц.

    Строка ``page_spec`` может содержать диапазоны страниц (``start-end``),
    одиночные номера или их комбинацию через запятую. Нумерация страниц
    1‑индексирована. Дубликаты игнорируются. Если передан ``total_pages``,
    функция дополнительно проверяет, что запрошенные номера не выходят
    за пределы [1, total_pages].

    :param page_spec: строка вида ``"1-3,5,7-9"``
    :param total_pages: общее число страниц в документе (для проверки границ)
    :raises ValueError: при некорректном формате, отрицательных или нулевых
        номерах, диапазонах с ``start > end`` или выходе за пределы
    :return: отсортированный список уникальных номеров страниц
    """
    if not isinstance(page_spec, str):
        raise ValueError("page_spec must be a string")
    numbers: set[int] = set()
    for raw_part in page_spec.split(','):
        part = raw_part.strip()
        if not part:
            continue
        m = _RANGE_RE.match(part)
        if m:
            start, end = map(int, m.groups())
            if start <= 0 or end <= 0:
                raise ValueError(f"Неверный диапазон: {part}")
            if start > end:
                raise ValueError(f"Начало диапазона больше конца: {part}")
            for i in range(start, end + 1):
                numbers.add(i)
            continue
        if _SINGLE_RE.match(part):
            num = int(part)
            if num <= 0:
                raise ValueError(f"Неверный номер страницы: {part}")
            numbers.add(num)
            continue
        # Если ни диапазон, ни одиночный номер, формат неверный
        raise ValueError(f"Неверный формат части списка: {part}")

    sorted_numbers = sorted(numbers)
    # Проверяем выход за границы, если известно общее число страниц
    if total_pages is not None:
        invalid = [n for n in sorted_numbers if n > total_pages]
        if invalid:
            raise ValueError(f"Некорректные номера страниц: {invalid}")
    return sorted_numbers


def extract_pages_pypdf(
    input_path: str,
    output_path: str,
    page_numbers: Sequence[int],
    copy_metadata: bool = False,
) -> None:
    """Извлечь указанные страницы из PDF с помощью библиотеки ``pypdf``.

    :param input_path: путь к исходному PDF‑файлу
    :param output_path: путь для сохранения результирующего PDF
    :param page_numbers: последовательность номеров страниц (1‑индексированных)
    :param copy_metadata: копировать метаданные из исходного файла
    :raises RuntimeError: если документ зашифрован
    """
    reader = pypdf.PdfReader(input_path)
    if reader.is_encrypted:
        raise RuntimeError("Зашифрованные PDF не поддерживаются") # TODO
    writer = pypdf.PdfWriter()
    for num in page_numbers:
        # 1‑индексация → 0‑индексация
        writer.add_page(reader.pages[num - 1])
    if copy_metadata and reader.metadata:
        writer.add_metadata(reader.metadata)
    # Обеспечиваем, что каталог для сохранения существует
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    # Сохраняем результат
    with open(output_path, "wb") as f:
        writer.write(f)

@click.command()
@click.option(
    "--input",
    "input_path",
    required=True,
    help="Имя исходного PDF (файл должен находиться в каталоге input_pdfs/ или указываться абсолютным путём)",
)
@click.option(
    "--pages",
    required=True,
    help="Диапазоны страниц, например '1-3,5,7-9'",
)
@click.option(
    "--output",
    default=None,
    help="Имя выходного файла (по умолчанию формируется автоматически)",
)
def main(input_path: str, pages: str, output: Optional[str]) -> None:
    """Точка входа командной строки.

    Скрипт валидирует входные параметры, парсит список страниц, извлекает
    указанныe страницы и сохраняет результат в каталог ``output_pdfs``.
    """
    # Проверяем расширение
    if not input_path.lower().endswith(".pdf"):
        raise click.BadParameter("Файл должен иметь расширение .pdf", param_hint="--input")

    # Определяем полный путь к файлу
    if os.path.isabs(input_path) and os.path.isfile(input_path):
        full_path = input_path
    else:
        candidate = os.path.join("input_pdfs", input_path)
        if os.path.isfile(candidate):
            full_path = candidate
        else:
            # Если файл не найден, сразу выдаём ошибку
            raise click.BadParameter(f"Файл не найден: {candidate}", param_hint="--input")

    # Открываем документ, чтобы узнать число страниц и проверить шифрование
    try:
        reader = pypdf.PdfReader(full_path)
    except Exception as exc:
        # Некорректный файл или повреждённый PDF
        raise click.BadParameter(f"Не удалось открыть файл: {exc}", param_hint="--input")

    if reader.is_encrypted:
        # Для простоты не запрашиваем пароль
        raise click.BadParameter(
            "Зашифрованные PDF не поддерживаются", param_hint="--input"
        )
    total_pages = len(reader.pages)

    # Разбираем список страниц
    try:
        page_numbers = parse_page_spec(pages, total_pages)
    except ValueError as err:
        raise click.BadParameter(str(err), param_hint="--pages") from err

    # Определяем имя выходного файла
    if output:
        out_name = output
    else:
        base = os.path.basename(input_path)
        name, _ext = os.path.splitext(base)
        out_name = f"{name}_pages.pdf"

    # Формируем путь для сохранения
    out_dir = "output_pdfs"
    os.makedirs(out_dir, exist_ok=True)
    output_path_full = os.path.join(out_dir, out_name)

    # Извлекаем страницы только с использованием pypdf
    try:
        extract_pages_pypdf(full_path, output_path_full, page_numbers)
    except RuntimeError as exc:
        raise click.BadParameter(str(exc)) from exc

    click.echo(f"Создан файл: {output_path_full}")


if __name__ == "__main__":  # pragma: no cover
    main()
