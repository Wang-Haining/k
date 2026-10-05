"""Archive evidence."""

import csv
import hashlib
import io
import json
import re
import zipfile
from collections import defaultdict
from pathlib import Path

from config import DATA_DIR
from construct.reporter import dump

F = DATA_DIR / "contemporaneous"
R = F / "sources"
P = F / "packets"
cases = json.loads((F / "review_cases.json").read_text())
ncts = {c["protocol"]["identificationModule"]["nctId"] for c in cases}
assert len(cases) >= 11724 and ncts, "Required source invariant failed; inspect the private input locally."
aliases = {
    c["protocol"]["identificationModule"]["nctId"]: c["protocol"]["identificationModule"].get("nctIdAliases", [])
    for c in cases
}
requested = ncts | {old for values in aliases.values() for old in values}
archive = R / "AACT-2022-11-09.zip"
assert hashlib.md5(archive.read_bytes()).hexdigest() == "1d4e6d141f40d300186fdd3d0a5980b1", (
    "Required source invariant failed; inspect the private input locally."
)
tables = {}
counts = {}
with zipfile.ZipFile(archive) as z:
    for name in ["overall_officials", "responsible_parties", "studies"]:
        rows = defaultdict(list)
        total = 0
        with z.open("AACT-2022-11-09/" + name + ".txt") as f:
            for row in csv.DictReader(io.TextIOWrapper(f), delimiter="|"):
                total += 1
                if row["nct_id"] in requested:
                    rows[row["nct_id"]].append(row)
        tables[name] = rows
        counts[name] = {"scanned": total, "retained": sum(map(len, rows.values()))}
assert (
    counts["studies"]["scanned"] == 432983
    and counts["overall_officials"]["scanned"] == 421439
    and (counts["responsible_parties"]["scanned"] == 414307)
), "Required source invariant failed; inspect the private input locally."
later = R / "AACT_20240927_responsible_parties.txt"
assert hashlib.md5(later.read_bytes()).hexdigest() == "7a05bfb5f6e64ff8dad4ff0f8696ca35", (
    "Required source invariant failed; inspect the private input locally."
)
later_rows = defaultdict(list)
total = 0
with later.open() as f:
    for row in csv.DictReader(f, delimiter="|"):
        total += 1
        if row["nct_id"] in requested:
            later_rows[row["nct_id"]].append(row)
counts["responsible_parties_20240927"] = {"scanned": total, "retained": sum(map(len, later_rows.values()))}
manifest = []
coverage = []
mask = (
    "(?i)\\b(?:(?:PA|PAR|PAS)-\\d{2}-\\d{3}|RFA-[A-Z]{2}-\\d{2}-\\d{3})\\b|(?:independ"
    "ent\\s+)?clinical\\s+trials?\\s+(?:not\\s+allowed|required|optional)"
)
for nct in sorted(requested):
    for stamp, snapshot, deposit, record, source, rows in [
        (
            "20221109",
            "2022-11-09",
            "2023-11-09",
            "10091147",
            "AACT-2022-11-09.zip",
            {name: table.get(nct, []) for name, table in tables.items()},
        ),
        (
            "20240927",
            "2024-09-27",
            "2024-10-23",
            "13984069",
            "responsible_parties.txt",
            {"responsible_parties": later_rows.get(nct, [])},
        ),
    ]:
        present = any(rows.values())
        coverage.append(
            {
                "nct_id": nct,
                "snapshot_date": snapshot,
                "record_present": present,
                "table_rows": {k: len(v) for k, v in rows.items()},
            }
        )
        if not present:
            continue
        assert len(rows.get("studies", [])) <= 1, "Required source invariant failed; inspect the private input locally."
        value = {
            "nct_id": nct,
            "provenance": {
                "source_record": "https://zenodo.org/records/" + record,
                "source_url": f"https://zenodo.org/records/{record}/files/{source}?download=1",
                "claimed_snapshot_date": snapshot,
                "public_deposit_date": deposit,
                "source_kind": "researcher_deposited_AACT_registry_snapshot",
                "dating_rule": (
                    "Use snapshot date as conservative historical observation date; whole-record"
                    " last_update_posted_date is not the date the PI role began. Never apply a h"
                    "istorical date to a current-only name. Missing rows are not evidence of abs"
                    "ence."
                ),
            },
            "verbatim_table_rows": rows,
        }
        text = re.sub(mask, "[funding designation redacted]", json.dumps(value, ensure_ascii=False, indent=2))
        dest = P / f"archive_{stamp}_{nct}.txt"
        if dest.exists():
            assert dest.read_text() == text, "Required source invariant failed; inspect the private input locally."
        else:
            dest.write_text(text)
        manifest.append(
            {
                "addendum_id": nct + "_AACT_" + stamp,
                "nct_id": nct,
                "evidence_kind": "historical_registry_snapshot",
                "source_url": value["provenance"]["source_url"],
                "snapshot_date": snapshot,
                "deposit_date": deposit,
                "local_text": str(dest.resolve()),
                "image_pages": [],
                "text_sha256": hashlib.sha256(text.encode()).hexdigest(),
                "method": value["provenance"]["dating_rule"],
            }
        )
base_manifest = list(manifest)
alias_count = 0
for canonical, old_ids in aliases.items():
    for old in old_ids:
        for item in base_manifest:
            if item["nct_id"] != old:
                continue
            value = json.loads(Path(item["local_text"]).read_text())
            value["explicit_current_registry_alias_binding"] = {
                "source": "https://clinicaltrials.gov/study/" + canonical,
                "nctId": canonical,
                "nctIdAliases": old_ids,
                "interpretation": (
                    "Official identifier linkage only. Compare historical/current titles and dat"
                    "es; do not assume identical protocol content or backdate current names."
                ),
            }
            dest = P / ("archive_alias_" + canonical + "_" + item["addendum_id"] + ".txt")
            text = json.dumps(value, ensure_ascii=False, indent=2)
            if dest.exists():
                assert dest.read_text() == text, "Required source invariant failed; inspect the private input locally."
            else:
                dest.write_text(text)
            manifest.append(
                dict(
                    item,
                    addendum_id=canonical + "_ALIAS_" + item["addendum_id"],
                    nct_id=canonical,
                    historical_nct_id=old,
                    local_text=str(dest.resolve()),
                    text_sha256=hashlib.sha256(text.encode()).hexdigest(),
                )
            )
            alias_count += 1
dump(F / "historical_registry_addenda.json", manifest)
dump(
    F / "historical_registry_source_coverage.json",
    {
        "review_candidates": len(cases),
        "unique_NCTs": len(ncts),
        "requested_identifiers_including_official_aliases": len(requested),
        "alias_addenda": alias_count,
        "tables": counts,
        "coverage": coverage,
        "addenda": len(manifest),
        "source_absence_interpretation": "Not present in this snapshot is not no PI role, no trial, or a zero outcome.",
    },
)
print("ARCHIVED SOURCES", len(cases), "pairs;", len(ncts), "NCTs;", len(manifest), "source supplements;")
