"""Bounded CSV numeric summaries, with decimal arithmetic and explicit missing-value handling."""
import csv
import io
import json
import sys
from decimal import Decimal, InvalidOperation, localcontext


def run(input_data: dict) -> dict:
    text = input_data.get("csv_text")
    column = input_data.get("column")
    if not isinstance(text, str) or len(text.encode()) > 500000 or not isinstance(column, str):
        raise ValueError("csv_text must be at most 500 KB and column must be a string")
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames or column not in reader.fieldnames or len(set(reader.fieldnames)) != len(reader.fieldnames):
        raise ValueError("Column is absent or headers are duplicated")
    count, missing = 0, 0
    total = Decimal(0)
    minimum = maximum = None
    with localcontext() as context:
        context.prec = 50
        for number, row in enumerate(reader, 1):
            if number > 10000 or None in row:
                raise ValueError("Too many rows or malformed CSV")
            raw = row.get(column)
            if raw is None or not raw.strip():
                missing += 1
                continue
            try:
                value = Decimal(raw.strip())
            except InvalidOperation as exc:
                raise ValueError(f"Non-numeric value at row {number}") from exc
            if not value.is_finite() or abs(value.adjusted()) > 12 or len(value.as_tuple().digits) > 24:
                raise ValueError("Values must be finite and within the supported precision/range")
            count += 1
            total += value
            minimum = value if minimum is None else min(minimum, value)
            maximum = value if maximum is None else max(maximum, value)
        def output(value):
            return format(value.normalize(), "f") if value is not None else None
        return {"count": count, "missing_count": missing, "sum": output(total),
                "mean": output(total/count) if count else None,
                "min": output(minimum), "max": output(maximum)}


if __name__ == "__main__":
    print(json.dumps(run(json.load(sys.stdin)), allow_nan=False))
