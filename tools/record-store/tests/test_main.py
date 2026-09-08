import pytest
from app.main import run


def test_persistent_read_and_replace():
    storage = {"action": "read", "record_type": "문자열 기록", "record_id": "unit_record"}
    assert run({"key": "unit_record"}) == {
        "key": "unit_record",
        "found": False,
        "value": None,
        "storage": storage,
    }
    for index, value in enumerate(["첫 번째", "quoted ' value; --", ""]):
        expected = {"key": "unit_record", "found": True, "value": value}
        assert run({"key": "unit_record", "value": value}) == {
            **expected,
            "storage": {**storage, "action": "created" if index == 0 else "updated"},
        }
        assert run({"key": "unit_record"}) == {**expected, "storage": storage}
        assert run({"key": "unit_record", "value": value})["storage"]["action"] == "reused"


@pytest.mark.parametrize(
    "data", [None, {}, {"key": "../escape"}, {"key": "x", "value": 1}, {"key": "x", "value": "x" * 10001}]
)
def test_invalid_input(data):
    with pytest.raises(ValueError):
        run(data)
