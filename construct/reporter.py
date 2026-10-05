"""Capture and replay paginated NIH RePORTER project searches."""

import csv
import json
import time
import urllib.request
from datetime import UTC, datetime

from config import DATA_DIR

RAW = DATA_DIR / "sources/reporter"
OUT = DATA_DIR / "cohort"


def dump(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2))


def table(path, rows, fields=None):
    assert rows or fields, "Empty table requires explicit columns"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields or list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    print("CSV rows:", len(rows))


def reporter(label, criteria, directory=None):
    directory = directory if directory is not None else RAW
    rows, offset = [], 0
    while True:
        payload = {"criteria": criteria, "offset": offset, "limit": 500, "sort_field": "appl_id", "sort_order": "asc"}
        path = directory / f"{label}_{offset}.json"
        if path.exists():
            saved = json.loads(path.read_text())
            assert saved["request"] == payload, "Frozen RePORTER request differs from the requested criteria"
            response = saved["response"]
        else:
            request = urllib.request.Request(
                "https://api.reporter.nih.gov/v2/projects/search",
                data=json.dumps(payload).encode(),
                headers={"Content-Type": "application/json"},
            )
            response = json.load(urllib.request.urlopen(request, timeout=90))
            dump(path, {"retrieved_at": datetime.now(UTC).isoformat(), "request": payload, "response": response})
            time.sleep(1.05)
        total = response["meta"]["total"]
        page = response["results"]
        rows.extend(page)
        if len(rows) == total:
            break
        assert page and len(rows) < total, f"inconsistent pagination: {len(rows)} of {total} rows"
        offset += len(page)
        assert offset <= 14999, f"RePORTER offset limit reached: {offset}"
    assert len({r["appl_id"] for r in rows}) == total, "Duplicate application IDs"
    print("RePORTER records:", len(rows))
    return rows
