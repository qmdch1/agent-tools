import pytest

from app.main import run


def test_decimal_arithmetic():
    assert run({"csv_text": "value\n0.1\n0.2\n", "column": "value"}) == {
        "count": 2, "missing_count": 0, "sum": "0.3", "mean": "0.15", "min": "0.1", "max": "0.2"}


def test_missing_values_and_negative():
    assert run({"csv_text": "id,value\na,-2\nb,\nc,6\n", "column": "value"}) == {
        "count": 2, "missing_count": 1, "sum": "4", "mean": "2", "min": "-2", "max": "6"}


def test_empty_column():
    assert run({"csv_text": "value\n", "column": "value"}) == {
        "count": 0, "missing_count": 0, "sum": "0", "mean": None, "min": None, "max": None}


@pytest.mark.parametrize("text", ["value\nNaN\n", "value\nInfinity\n", "value\nhello\n",
                                  "wrong\n1\n", "value,value\n1,2\n", "value\n1e99\n"])
def test_invalid_input(text):
    with pytest.raises(ValueError):
        run({"csv_text": text, "column": "value"})
