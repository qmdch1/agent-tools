import pytest
from app.main import run


def test_persistent_read_and_replace():
    assert run({"key": "unit_record"}) == {"key": "unit_record", "found": False, "value": None}
    for value in ["첫 번째", "quoted ' value; --", ""]:
        expected = {"key": "unit_record", "found": True, "value": value}
        assert run({"key": "unit_record", "value": value}) == expected
        assert run({"key": "unit_record"}) == expected


@pytest.mark.parametrize(
    "data", [None, {}, {"key": "../escape"}, {"key": "x", "value": 1}, {"key": "x", "value": "x" * 10001}]
)
def test_invalid_input(data):
    with pytest.raises(ValueError):
        run(data)
