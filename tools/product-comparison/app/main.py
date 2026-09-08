"""Compare supplied, sourced specifications; never retrieve or infer product facts."""

import json
import math
import sys
from datetime import date
from urllib.parse import urlsplit


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


def run(input_data: dict) -> dict:
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


if __name__ == "__main__":
    try:
        print(json.dumps(run(json.load(sys.stdin)), ensure_ascii=False, allow_nan=False))
    except (ValueError, TypeError, KeyError) as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
