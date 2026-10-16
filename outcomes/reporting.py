"Derive private awardee-level K-trial reporting eligibility and results indicators."

import csv
import json
from collections import defaultdict

from config import DATA_DIR
from outcomes.extended import plus_days

INSTRUMENT_DIR, HD, RV = (
    DATA_DIR / "instrument",
    DATA_DIR / "historical",
    DATA_DIR / "derived",
)
DUE = "2025-09-27"


def stratum(p):
    if p["period"] == "post_policy":
        return "post"
    return "pre_legacy" if int(p["year"]) >= 2018 else "pre_early"


def reporting(pa, feats):
    by = defaultdict(list)
    for r in csv.DictReader((RV / "ktrial_pairs.csv").open()):
        if r["analysis"] == "historical" and r["window"] == "inside" and (r["blind_id"] in pa):
            by[r["blind_id"]].append(feats[r["nct_id"]])
    rows = []
    for b, p in pa.items():
        due = [
            f
            for f in by.get(b, [])
            if f["status"] == "COMPLETED" and f["primary_completion"] and (f["primary_completion"][:10] <= DUE)
        ]
        rows.append(
            {
                "blind_id": b,
                "stratum": stratum(p),
                "ktrial_due": int(bool(due)),
                "ktrial_due_results": int(any(f["has_results"] for f in due)),
                "ktrial_due_results12": int(
                    any(
                        f["results_first_submitted"]
                        and f["results_first_submitted"][:10] <= plus_days(f["primary_completion"], 365)
                        for f in due
                    )
                ),
            }
        )
    return rows


def write(path, rows):
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
        print("CSV rows:", len(rows))


def main():
    RV.mkdir(parents=True, exist_ok=True)
    pa = {r["blind_id"]: r for r in csv.DictReader((HD / "person_analysis.csv").open())}
    feats = json.loads((INSTRUMENT_DIR / "trial_features.json").read_text())
    write(RV / "historical_reporting.csv", reporting(pa, feats))


if __name__ == "__main__":
    main()
    print("outcomes/reporting.py: complete")
