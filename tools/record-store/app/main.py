"""Persist small named text records using only the platform-provided database binding."""

import json
import os
import re
import sys

import psycopg


def run(input_data: dict) -> dict:
    if not isinstance(input_data, dict) or set(input_data) - {"key", "value"}:
        raise ValueError("Expected key and optional value")
    key = input_data.get("key")
    if not isinstance(key, str) or not re.fullmatch(r"[a-z][a-z0-9_]{0,79}", key):
        raise ValueError("Invalid record key")
    if "value" in input_data and (
        not isinstance(input_data["value"], str) or len(input_data["value"]) > 10000
    ):
        raise ValueError("Value must be text of at most 10000 characters")
    with psycopg.connect(os.environ["FOUNDRY_TOOL_DATABASE_URL"]) as conn:
        if "value" in input_data:
            # Serialize replacement by schema/key without a key constraint or a global table lock.
            conn.execute(
                "SELECT pg_advisory_xact_lock(hashtextextended(current_schema() || ':' || %s, 0))",
                (key,),
            )
            conn.execute("DELETE FROM records WHERE record_key=%s", (key,))
            conn.execute(
                "INSERT INTO records(record_key,record_value) VALUES (%s,%s)",
                (key, input_data["value"]),
            )
        rows = conn.execute("SELECT record_value FROM records WHERE record_key=%s LIMIT 2", (key,)).fetchall()
        if len(rows) > 1:
            raise ValueError("Duplicate record requires reconciliation")
        return {"key": key, "found": bool(rows), "value": rows[0][0] if rows else None}


if __name__ == "__main__":
    print(json.dumps(run(json.load(sys.stdin)), ensure_ascii=False, allow_nan=False))
