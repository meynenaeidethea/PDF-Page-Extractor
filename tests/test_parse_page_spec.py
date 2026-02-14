import pytest

from src.extract_pages import parse_page_spec


def test_parse_single_numbers_sorted_unique():
    assert parse_page_spec("3,1,2,2") == [1, 2, 3]


def test_parse_ranges_and_numbers_combo():
    assert parse_page_spec("1-3,5,7-9") == [1, 2, 3, 5, 7, 8, 9]


def test_parse_ignores_empty_parts_and_spaces():
    assert parse_page_spec(" 1-2 , , 4 , 4 ") == [1, 2, 4]


@pytest.mark.parametrize("spec", ["", " , , "])
def test_parse_empty_string_returns_empty_list(spec):
    assert parse_page_spec(spec) == []


@pytest.mark.parametrize(
    "spec",
    [
        "0",
        "-1",
        "1-0",
        "3-2",          # start > end
        "a",
        "1-a",
        "1--2",
        "1-2-3",
        "1..3",
        "1;2",
    ],
)
def test_parse_invalid_formats_raise_value_error(spec):
    with pytest.raises(ValueError):
        parse_page_spec(spec)


def test_parse_checks_total_pages_upper_bound():
    with pytest.raises(ValueError) as e:
        parse_page_spec("1,2,10", total_pages=5)
    assert "Некорректные номера страниц" in str(e.value)
