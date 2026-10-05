"""Summarize new-trial design and reporting characteristics from private pair outcomes."""

import csv
import json
import statistics
from collections import defaultdict

from config import DATA_DIR, RESULTS_DIR

OUT = RESULTS_DIR
FREEZE = "2025-09-27"


(OUT / "supplementary").mkdir(parents=True, exist_ok=True)


def person_table(pair_file, nct_of):
    feats = json.loads((DATA_DIR / "instrument" / "trial_features.json").read_text())
    by = defaultdict(list)
    for r in csv.DictReader(pair_file.open()):
        if r["primary_pair"] == "True":
            by[r["blind_id"]].append(feats[nct_of[r["case_id"]]])
    return by


def describe(trials):
    if not trials:
        return {}
    enr = [f["enrollment"] for f in trials if f["enrollment"] is not None]
    due = [
        f
        for f in trials
        if f["status"] == "COMPLETED" and f["primary_completion"] and (f["primary_completion"][:10] <= FREEZE)
    ]
    return {
        "n_trials": len(trials),
        "median_enrollment": statistics.median(enr) if enr else "",
        "pct_randomized": round(100 * sum(f["randomized"] for f in trials) / len(trials), 1),
        "pct_pilot_titled": round(100 * sum(f["pilot_in_title"] for f in trials) / len(trials), 1),
        "pct_enrollment_ge100": round(100 * sum((f["enrollment"] or 0) >= 100 for f in trials) / len(trials), 1),
        "n_completed_due": len(due),
        "pct_results_posted_among_due": round(100 * sum(f["has_results"] for f in due) / len(due), 1) if due else "",
    }


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    persons = {r["blind_id"]: r for r in csv.DictReader((DATA_DIR / "contemporaneous" / "person_analysis.csv").open())}
    bh = {r["blind_id"]: r for r in csv.DictReader((DATA_DIR / "historical" / "person_analysis.csv").open())}
    nct_main = {
        r["case_id"]: r["nct_id"]
        for r in csv.DictReader((DATA_DIR / "instrument" / "instrument_pair_outcomes.csv").open())
    }
    nct_bh = {r["case_id"]: r["nct_id"] for r in csv.DictReader((DATA_DIR / "historical" / "pairs.csv").open())}
    elig = [b for b, p in persons.items() if p["eligible_main"] == "1"]
    main_trials = person_table(DATA_DIR / "instrument" / "instrument_pair_outcomes.csv", nct_main)
    bh_trials = person_table(DATA_DIR / "historical" / "pair_outcomes.csv", nct_bh)
    desc = []
    for m in ("K23", "K08"):
        for g in ("Required", "Not Allowed"):
            ids = [b for b in elig if persons[b]["mechanism"] == m and persons[b]["group"] == g]
            desc.append(
                {
                    "analysis": "main",
                    "mechanism": m,
                    "cell": g,
                    "n_people": len(ids),
                    **describe([f for b in ids for f in main_trials.get(b, [])]),
                }
            )
        for per in ("pre_policy", "post_policy"):
            for i in ("1", "0"):
                ids = [b for b in bh if bh[b]["mechanism"] == m and bh[b]["period"] == per and (bh[b]["intent"] == i)]
                desc.append(
                    {
                        "analysis": "historical",
                        "mechanism": m,
                        "cell": f"{per}|intent{i}",
                        "n_people": len(ids),
                        **describe([f for b in ids for f in bh_trials.get(b, [])]),
                    }
                )
    for name, data in (("supplementary/new_trial_characteristics.csv", desc),):
        keys = sorted({k for d in data for k in d}, key=lambda k: list(data[0]).index(k) if k in data[0] else 99)
        with (OUT / name).open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=keys, lineterminator="\n")
            w.writeheader()
            w.writerows(data)
            print("CSV rows:", len(data))


if __name__ == "__main__":
    main()
    print("analysis/trial_quality.py: complete")
