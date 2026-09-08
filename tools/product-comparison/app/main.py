"""Compare supplied, sourced specifications; never retrieve or infer product facts."""

import hashlib
import json
import math
import os
import re
import sys
from datetime import date
from urllib.parse import urlsplit

import psycopg
from psycopg.types.json import Jsonb


def require(condition, message):
    if not condition:
        raise ValueError(message)


def text(value, limit=200):
    return isinstance(value, str) and 0 < len(value.strip()) <= limit


def value_ok(value, kind):
    if kind == "number":
        return type(value) in (int, float) and abs(value) <= 1e15 and math.isfinite(value)
    if kind == "boolean":
        return type(value) is bool
    return text(value, 1000)


def compare(input_data: dict) -> dict:
    require(isinstance(input_data, dict) and set(input_data) == {"payload"}, "Expected payload")
    data = input_data["payload"]
    require(isinstance(data, dict), "Payload must be an object")
    require(set(data) <= {"fields", "products", "filters", "sort", "limit"}, "Unknown option")
    fields, products = data.get("fields"), data.get("products")
    require(isinstance(fields, dict) and 1 <= len(fields) <= 30, "Declare 1..30 fields")
    for name, definition in fields.items():
        require(text(name, 80) and isinstance(definition, dict), "Invalid field")
        require(set(definition) == {"type", "unit"}, "Field requires type and unit")
        require(definition["type"] in ("number", "string", "boolean"), "Invalid type")
        require(
            text(definition["unit"], 40) if definition["type"] == "number" else definition["unit"] is None,
            "Numeric fields require explicit units",
        )
    require(isinstance(products, list) and 1 <= len(products) <= 100, "Supply 1..100 products")
    normalized, seen = [], set()
    for product in products:
        require(
            isinstance(product, dict) and set(product) == {"id", "name", "sources", "specs"},
            "Product requires id, name, sources and specs",
        )
        require(text(product["id"], 100) and product["id"] not in seen, "Invalid/duplicate id")
        seen.add(product["id"])
        require(text(product["name"]), "Invalid product name")
        sources = product["sources"]
        require(isinstance(sources, list) and 1 <= len(sources) <= 10, "Sources required")
        for source in sources:
            require(isinstance(source, dict) and set(source) == {"url", "checked_at"}, "Invalid source")
            require(text(source["url"], 2000), "Invalid URL")
            url = urlsplit(source["url"])
            require(
                url.scheme == "https"
                and bool(url.hostname)
                and not url.username
                and not url.password
                and not any(c.isspace() for c in source["url"]),
                "Use HTTPS source URL",
            )
            checked = source["checked_at"]
            require(isinstance(checked, str) and len(checked) == 10, "Use YYYY-MM-DD")
            require(date.fromisoformat(checked).isoformat() == checked, "Invalid date")
        specs = product["specs"]
        require(isinstance(specs, dict) and set(specs) <= set(fields), "Undeclared specification")
        cells = {}
        for name, definition in fields.items():
            cell = specs.get(name)
            if cell is None:
                cells[name] = {"value": None, "unit": definition["unit"], "status": "unknown"}
                continue
            require(isinstance(cell, dict) and set(cell) == {"value", "unit"}, "Invalid cell")
            require(cell["unit"] == definition["unit"], "Unit mismatch; convert explicitly before input")
            require(value_ok(cell["value"], definition["type"]), "Specification type mismatch")
            cells[name] = {**cell, "status": "provided"}
        normalized.append({"id": product["id"], "name": product["name"], "sources": sources, "specs": cells})
    filters = data.get("filters", [])
    require(isinstance(filters, list) and len(filters) <= 30, "Invalid filters")
    for condition in filters:
        require(
            isinstance(condition, dict) and set(condition) == {"field", "op", "value", "unit"},
            "Invalid filter",
        )
        field, op = condition["field"], condition["op"]
        require(isinstance(field, str) and field in fields, "Unknown filter field")
        definition = fields[field]
        require(op in ("eq", "gte", "lte"), "Invalid filter operator")
        require(op == "eq" or definition["type"] == "number", "Range requires numeric field")
        require(
            condition["unit"] == definition["unit"] and value_ok(condition["value"], definition["type"]),
            "Filter type/unit mismatch",
        )
    sort = data.get("sort")
    if sort is not None:
        require(isinstance(sort, dict) and set(sort) == {"field", "direction"}, "Invalid sort")
        require(
            isinstance(sort["field"], str)
            and sort["field"] in fields
            and sort["direction"] in ("asc", "desc"),
            "Invalid sort field/direction",
        )
    limit = data.get("limit", 100)
    require(type(limit) is int and 1 <= limit <= 100, "Invalid limit")
    matches, excluded = [], []
    for product in normalized:
        reasons = []
        for condition in filters:
            cell = product["specs"][condition["field"]]
            value, expected, op = cell["value"], condition["value"], condition["op"]
            if value is None:
                reasons.append({"field": condition["field"], "reason": "unknown"})
            elif not (
                value == expected if op == "eq" else value >= expected if op == "gte" else value <= expected
            ):
                reasons.append({"field": condition["field"], "reason": "condition_not_met"})
        if reasons:
            excluded.append({"id": product["id"], "reasons": reasons})
        else:
            matches.append(product)
    if sort:
        field = sort["field"]
        known = [p for p in matches if p["specs"][field]["value"] is not None]
        unknown = [p for p in matches if p["specs"][field]["value"] is None]
        matches = (
            sorted(known, key=lambda p: p["specs"][field]["value"], reverse=sort["direction"] == "desc")
            + unknown
        )
    return {
        "fields": fields,
        "products": matches[:limit],
        "matched_count": len(matches),
        "returned_count": min(limit, len(matches)),
        "excluded": excluded,
    }


def run(input_data: dict) -> dict:
    require(isinstance(input_data, dict) and set(input_data) == {"payload"}, "Expected payload")
    data = input_data["payload"]
    require(isinstance(data, dict), "Payload must be an object")
    action = data.get("action", "compare")
    require(action in ("compare", "get", "list"), "Unknown action")
    if action == "compare":
        payload = {k: v for k, v in data.items() if k != "action"}
        result = compare({"payload": payload})
        canonical = json.dumps(
            payload, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(",", ":")
        )
        require(len(canonical.encode()) <= 500000, "Comparison exceeds 500000 bytes")
        compare_id = hashlib.sha256(canonical.encode()).hexdigest()
        result = {**result, "compare_id": compare_id}
        with psycopg.connect(os.environ["FOUNDRY_TOOL_DATABASE_URL"]) as conn:
            conn.execute(
                "SELECT pg_advisory_xact_lock(hashtextextended(current_schema() || ':' || %s, 0))",
                (compare_id,),
            )
            rows = conn.execute(
                "SELECT request_data, result_data FROM comparisons WHERE compare_id=%s LIMIT 2", (compare_id,)
            ).fetchall()
            require(len(rows) <= 1, "Duplicate comparison requires reconciliation")
            if rows:
                require(rows[0][0] == payload, "Comparison identity conflict")
                result = rows[0][1]
            else:
                conn.execute(
                    "INSERT INTO comparisons(compare_id, request_data, result_data, created_at) VALUES (%s,%s,%s,now())",
                    (compare_id, Jsonb(payload), Jsonb(result)),
                )
        return {
            **result,
            "storage": {
                "action": "reused" if rows else "created",
                "record_type": "상품 비교",
                "record_id": compare_id,
            },
        }
    if action == "get":
        require(set(data) == {"action", "compare_id"}, "Get requires compare_id only")
        compare_id = data["compare_id"]
        require(
            isinstance(compare_id, str) and re.fullmatch(r"[0-9a-f]{64}", compare_id), "Invalid compare_id"
        )
        with psycopg.connect(os.environ["FOUNDRY_TOOL_DATABASE_URL"]) as conn:
            rows = conn.execute(
                "SELECT request_data, result_data FROM comparisons WHERE compare_id=%s LIMIT 2", (compare_id,)
            ).fetchall()
        require(len(rows) <= 1, "Duplicate comparison requires reconciliation")
        return {
            "compare_id": compare_id,
            "found": bool(rows),
            "request": rows[0][0] if rows else None,
            "result": rows[0][1] if rows else None,
            "storage": {"action": "read", "record_type": "상품 비교", "record_id": compare_id},
        }
    require(set(data) <= {"action", "limit", "offset"}, "Unknown list option")
    limit, offset = data.get("limit", 20), data.get("offset", 0)
    require(type(limit) is int and 1 <= limit <= 100, "Invalid list limit")
    require(type(offset) is int and 0 <= offset <= 10000, "Invalid list offset")
    with psycopg.connect(os.environ["FOUNDRY_TOOL_DATABASE_URL"]) as conn:
        rows = conn.execute(
            "SELECT compare_id,created_at,result_data->>'matched_count',result_data->>'returned_count' FROM comparisons ORDER BY created_at DESC,compare_id LIMIT %s OFFSET %s",
            (limit + 1, offset),
        ).fetchall()
    return {
        "comparisons": [
            {
                "compare_id": row[0],
                "created_at": row[1].isoformat(),
                "matched_count": int(row[2]),
                "returned_count": int(row[3]),
            }
            for row in rows[:limit]
        ],
        "has_more": len(rows) > limit,
        "offset": offset,
        "storage": {"action": "read", "record_type": "상품 비교 목록"},
    }


if __name__ == "__main__":
    try:
        print(json.dumps(run(json.load(sys.stdin)), ensure_ascii=False, allow_nan=False))
    except (ValueError, TypeError, KeyError) as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
