"Aggregate abstract-classifier intent among eligible contemporaneous awardees."

import csv
import json
import os
from collections import defaultdict

from config import DATA_DIR, RESULTS_DIR


def main():
    d = {r["blind_id"]: r for r in csv.DictReader((DATA_DIR / "contemporaneous" / "person_analysis.csv").open())}
    if os.environ.get("PUBLIC") == "1":
        call = {
            r["blind_id"]: "own_trial_planned" if r["intent"] == "1" else "not_own_trial"
            for r in csv.DictReader((DATA_DIR / "historical/person_analysis.csv").open())
        }
    else:
        call = {
            p.stem: json.loads(p.read_text())["label"]["research_type"]
            for p in (DATA_DIR / "historical" / "intent_labels").glob("*.json")
        }
    cnt = defaultdict(lambda: [0, 0])
    for b, r in d.items():
        if r.get("eligible_main") == "1":
            cnt[r["mechanism"], r["group"]][0] += call[b] == "own_trial_planned"
            cnt[r["mechanism"], r["group"]][1] += 1
    rows = [
        {"mechanism": m, "group": g, "n_intent": a, "n": n, "pct_intent": round(100 * a / n, 1)}
        for (m, g), (a, n) in sorted(cnt.items())
    ]
    with (RESULTS_DIR / "contemporaneous" / "intent.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
        print("CSV rows:", len(rows))


if __name__ == "__main__":
    main()
    print("analysis/contemporaneous_intent.py: complete")
