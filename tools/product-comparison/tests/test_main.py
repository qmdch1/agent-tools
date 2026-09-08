from copy import deepcopy

import pytest
from app.main import run


def sample():
    return {
        "payload": {
            "fields": {
                "rating": {"type": "number", "unit": "m"},
                "certified": {"type": "boolean", "unit": None},
            },
            "products": [
                {
                    "id": "a",
                    "name": "Sample A",
                    "sources": [{"url": "https://example.com/a", "checked_at": "2026-09-08"}],
                    "specs": {"rating": {"value": 200, "unit": "m"}},
                }
            ],
            "filters": [{"field": "rating", "op": "gte", "value": 200, "unit": "m"}],
        }
    }


def test_rating_does_not_infer_certification():
    result = run(sample())
    assert result["matched_count"] == 1
    assert result["products"][0]["specs"]["certified"] == {"value": None, "unit": None, "status": "unknown"}


def test_missing_filter_is_excluded_with_reason():
    data = sample()
    data["payload"]["filters"] = [{"field": "certified", "op": "eq", "value": True, "unit": None}]
    result = run(data)
    assert result["products"] == []
    assert result["excluded"] == [{"id": "a", "reasons": [{"field": "certified", "reason": "unknown"}]}]


@pytest.mark.parametrize("value", [True, "200", float("nan"), float("inf"), None])
def test_numeric_type_rejected(value):
    data = sample()
    data["payload"]["products"][0]["specs"]["rating"]["value"] = value
    with pytest.raises(ValueError):
        run(data)


@pytest.mark.parametrize("location", ["cell", "filter"])
def test_unit_mismatch(location):
    data = sample()
    cell = (
        data["payload"]["filters"][0]
        if location == "filter"
        else data["payload"]["products"][0]["specs"]["rating"]
    )
    cell["unit"] = "ft"
    with pytest.raises(ValueError):
        run(data)


@pytest.mark.parametrize(
    "source",
    [
        {"url": "http://example.com", "checked_at": "2026-09-08"},
        {"url": "https://user:pass@example.com", "checked_at": "2026-09-08"},
        {"url": "https://example.com", "checked_at": "2026-02-30"},
        {"url": "https://example.com", "checked_at": "20260908"},
    ],
)
def test_invalid_provenance(source):
    data = sample()
    data["payload"]["products"][0]["sources"] = [source]
    with pytest.raises(ValueError):
        run(data)


def test_sort_unknown_last_both_directions_and_limit():
    data = sample()
    a = data["payload"]["products"][0]
    b, c, d = deepcopy(a), deepcopy(a), deepcopy(a)
    b["id"], c["id"], d["id"] = "b", "c", "d"
    b["specs"]["rating"] = None
    c["specs"]["rating"]["value"] = 100
    data["payload"].update(products=[a, b, c, d], filters=[])
    for direction, expected in [("asc", ["c", "a", "d", "b"]), ("desc", ["a", "d", "c", "b"])]:
        data["payload"]["sort"] = {"field": "rating", "direction": direction}
        assert [p["id"] for p in run(data)["products"]] == expected
    data["payload"]["limit"] = 2
    result = run(data)
    assert result["matched_count"] == 4 and result["returned_count"] == 2


def test_input_unchanged_and_repeatable():
    data = sample()
    before = deepcopy(data)
    assert run(data) == run(data)
    assert data == before


def test_duplicate_identifier():
    data = sample()
    data["payload"]["products"] *= 2
    with pytest.raises(ValueError):
        run(data)


def test_no_match_and_strict_text_comparison():
    data = sample()
    data["payload"]["fields"]["crystal"] = {"type": "string", "unit": None}
    data["payload"]["products"][0]["specs"]["crystal"] = {"value": "sapphire", "unit": None}
    data["payload"]["filters"] = [{"field": "crystal", "op": "eq", "value": "Sapphire", "unit": None}]
    assert run(data)["matched_count"] == 0


@pytest.mark.parametrize(
    "option", [{"limit": True}, {"sort": {"field": "missing", "direction": "asc"}}, {"unexpected": 1}]
)
def test_bad_options(option):
    data = sample()
    data["payload"].update(option)
    with pytest.raises(ValueError):
        run(data)
