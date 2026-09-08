import os
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy

import psycopg
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


def test_save_get_roundtrip_and_missing():
    data = sample()
    result = run(data)
    saved = run({"payload": {"action": "get", "compare_id": result["compare_id"]}})
    assert saved == {
        "compare_id": result["compare_id"],
        "found": True,
        "request": data["payload"],
        "result": result,
    }
    missing = run({"payload": {"action": "get", "compare_id": "0" * 64}})
    assert missing["found"] is False and missing["result"] is None


def test_concurrent_save_is_idempotent_and_changed_input_new_snapshot():
    data = sample()
    data["payload"]["products"][0]["id"] = "concurrent"
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: run(data), range(4)))
    assert all(result == results[0] for result in results)
    with psycopg.connect(os.environ["FOUNDRY_TOOL_DATABASE_URL"]) as conn:
        assert (
            conn.execute(
                "SELECT count(*) FROM comparisons WHERE compare_id=%s", (results[0]["compare_id"],)
            ).fetchone()[0]
            == 1
        )
    data["payload"]["products"][0]["sources"][0]["checked_at"] = "2026-09-09"
    assert run(data)["compare_id"] != results[0]["compare_id"]


def test_list_bounded_and_invalid_input_not_saved():
    result = run(sample())
    listing = run({"payload": {"action": "list", "limit": 100}})
    assert result["compare_id"] in [item["compare_id"] for item in listing["comparisons"]]
    assert len(run({"payload": {"action": "list", "limit": 1}})["comparisons"]) == 1
    assert run({"payload": {"action": "list", "offset": 10000}})["comparisons"] == []
    with psycopg.connect(os.environ["FOUNDRY_TOOL_DATABASE_URL"]) as conn:
        before = conn.execute("SELECT count(*) FROM comparisons").fetchone()[0]
    data = sample()
    data["payload"]["products"][0]["sources"][0]["url"] = "bad"
    with pytest.raises(ValueError):
        run(data)
    with psycopg.connect(os.environ["FOUNDRY_TOOL_DATABASE_URL"]) as conn:
        assert conn.execute("SELECT count(*) FROM comparisons").fetchone()[0] == before
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute("SELECT * FROM agent.programs LIMIT 1")


@pytest.mark.parametrize(
    "payload",
    [
        {"action": "drop"},
        {"action": "get", "compare_id": "' OR 1=1"},
        {"action": "list", "limit": True},
        {"action": "list", "offset": -1},
        {"action": "list", "sql": "SELECT 1"},
    ],
)
def test_storage_input_validation(payload):
    with pytest.raises(ValueError):
        run({"payload": payload})
