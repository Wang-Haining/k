"Build private awardee-level sensitivity outcomes from frozen pair classifications."

import csv
import json
from datetime import date

from config import DATA_DIR
from outcomes.dates import interval

INSTRUMENT_DIR = DATA_DIR / "instrument"
OUT = INSTRUMENT_DIR / "analysis"


def years_after(start, k_start):
    lo, _ = interval(start)
    return (date.fromisoformat(lo) - date.fromisoformat(k_start)).days / 365.25


def main():
    key = {r["blind_id"]: r for r in json.loads((DATA_DIR / "contemporaneous" / "cohort_key_private.json").read_text())}
    pairs = list(csv.DictReader((INSTRUMENT_DIR / "instrument_pair_outcomes.csv").open()))
    by = {}
    for r in pairs:
        by.setdefault(r["blind_id"], []).append(r)

    def T(v):
        return v == "True"

    variants = {
        "main": lambda r: True,
        "window_4y": lambda r: years_after(r["start_date"], key[r["blind_id"]]["start_date"]) <= 4.0,
        "excl_basic_science": lambda r: r["primary_purpose"] != "BASIC_SCIENCE",
        "excl_withdrawn_zero": lambda r: not T(r["flag_withdrawn_zero"]),
        "excl_start_conflict": lambda r: not T(r["flag_start_conflict"]),
        "registry_roles_only": lambda r: r["role_source"] in ("current_registry", "historical_snapshot"),
        "current_record_only": lambda r: r["role_source"] == "current_registry",
    }
    rows = []
    for b, k in sorted(key.items()):
        rs = by.get(b, [])
        row = {"blind_id": b, "org_id": k["org_id"], "institution": k["institution"]}
        for name, keep in variants.items():
            sec = [r for r in rs if T(r["secondary_pair"]) and keep(r)]
            pri = [r for r in sec if T(r["primary_pair"])]
            row[f"secondary_{name}"] = int(bool(sec))
            row[f"primary_{name}"] = int(bool(pri))
        pri = [r for r in rs if T(r["primary_pair"])]
        sec = [r for r in rs if T(r["secondary_pair"])]
        row["t_first_primary"] = round(
            min((years_after(r["start_date"], k["start_date"]) for r in pri), default=float("nan")), 3
        )
        row["t_first_secondary"] = round(
            min((years_after(r["start_date"], k["start_date"]) for r in sec), default=float("nan")), 3
        )
        row["n_primary_trials"] = len(pri)
        row["preK_PI"] = int(any(T(r["preK_pair"]) for r in rs))
        row["unresolved"] = int(any(T(r["timing_unresolved_pair"]) for r in rs) and (not sec))
        rows.append(row)
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "person_variants.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
        print("CSV rows:", len(rows))


if __name__ == "__main__":
    main()
    print("outcomes/contemporaneous_variants.py: complete")
