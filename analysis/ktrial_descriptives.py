"Summarize K-trial cells, fiscal-year trajectories, and trial characteristics."

import csv
import json
import os
import statistics

from config import DATA_DIR, RESULTS_DIR
from outcomes.extended import timely

OUT = RESULTS_DIR
RV, HD = (DATA_DIR / "derived", DATA_DIR / "historical")
DUE = "2025-09-27"


(OUT / "historical").mkdir(parents=True, exist_ok=True)
(OUT / "supplementary").mkdir(parents=True, exist_ok=True)


def pct(xs):
    return round(100 * sum(xs) / len(xs), 1) if xs else ""


def write(name, rows):
    with (OUT / name).open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
        print("CSV rows:", len(rows))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    pa = {r["blind_id"]: r for r in csv.DictReader((HD / "person_analysis.csv").open())}
    extended = {r["blind_id"]: r for r in csv.DictReader((RV / "historical_extended.csv").open())}
    ids = [b for b in pa if extended[b]["besh_only_classifier"] == "0"]
    cells = []
    for m in ("K23", "K08"):
        for per in ("pre_policy", "post_policy"):
            for it in ("1", "0"):
                g = [b for b in ids if pa[b]["mechanism"] == m and pa[b]["period"] == per and (pa[b]["intent"] == it)]

                def f(c, g=g):
                    return pct([int(extended[b][c]) for b in g])

                cells.append(
                    {
                        "mechanism": m,
                        "period": per,
                        "intent": it,
                        "n": len(g),
                        "ktrial_direct": f("ktrial_direct"),
                        "ktrial_any_start": f("ktrial_any_start"),
                        "ktrial_grant_linked": f("ktrial_grant_linked"),
                        "ktrial_judged_unlinked": f("ktrial_judged_unlinked"),
                        "any_trial": pct([int(pa[b]["secondary"]) for b in g]),
                        "new_trial": pct([int(pa[b]["primary"]) for b in g]),
                        "new_trial_without_ktrial": pct(
                            [int(pa[b]["primary"] == "1" and extended[b]["ktrial_direct"] == "0") for b in g]
                        ),
                    }
                )
    write("supplementary/ktrial_cells.csv", cells)
    yr = []
    for m in ("K23", "K08"):
        for it in ("1", "0"):
            pre = [b for b in ids if pa[b]["mechanism"] == m and pa[b]["intent"] == it]
            for y in sorted({int(pa[b]["year"]) for b in pre}):
                for per in ("pre_policy", "post_policy"):
                    g = [b for b in pre if int(pa[b]["year"]) == y and pa[b]["period"] == per]
                    if g:
                        yr.append(
                            {
                                "mechanism": m,
                                "intent": it,
                                "fiscal_year": y,
                                "period": per,
                                "n": len(g),
                                "ktrial_direct": pct([int(extended[b]["ktrial_direct"]) for b in g]),
                                "ktrial_grant_linked": pct([int(extended[b]["ktrial_grant_linked"]) for b in g]),
                                "new_trial": pct([int(pa[b]["primary"]) for b in g]),
                                "k_ktrial": sum(int(extended[b]["ktrial_direct"]) for b in g),
                                "k_new_trial": sum(int(pa[b]["primary"]) for b in g),
                            }
                        )
    write("historical/ktrial_by_year.csv", yr)
    if os.environ.get("PUBLIC") == "1":
        return
    feats = json.loads((DATA_DIR / "instrument" / "trial_features.json").read_text())
    first = {}
    for r in csv.DictReader((RV / "ktrial_pairs.csv").open()):
        if (
            r["analysis"] == "historical"
            and r["blind_id"] in pa
            and extended[r["blind_id"]]["besh_only_classifier"] == "0"
            and (r["blind_id"] not in first or r["start_date"] < first[r["blind_id"]]["start_date"])
        ):
            first[r["blind_id"]] = r
    ch = []
    for m in ("K23", "K08"):
        for per in ("pre_policy", "post_policy"):
            sel = [
                r
                for b, r in first.items()
                if pa[b]["mechanism"] == m and pa[b]["period"] == per and (pa[b]["intent"] == "1")
            ]
            tr = [feats[r["nct_id"]] for r in sel]
            due = [
                f
                for f in tr
                if f["status"] == "COMPLETED" and f["primary_completion"] and (f["primary_completion"][:10] <= DUE)
            ]
            ch.append(
                {
                    "mechanism": m,
                    "period": per,
                    "n_k_trials": len(tr),
                    "median_enrollment": statistics.median([f["enrollment"] or 0 for f in tr]) if tr else "",
                    "enrollment_ge100_pct": pct([(f["enrollment"] or 0) >= 100 for f in tr]),
                    "randomized_pct": pct([f["randomized"] for f in tr]),
                    "multisite_ge3_pct": pct([f["n_sites"] >= 3 for f in tr]),
                    "phase2plus_pct": pct([bool(set(f["phases"]) & {"PHASE2", "PHASE3", "PHASE4"}) for f in tr]),
                    "completed_pct": pct([f["status"] == "COMPLETED" for f in tr]),
                    "terminated_or_withdrawn_pct": pct([f["status"] in ("TERMINATED", "WITHDRAWN") for f in tr]),
                    "ongoing_pct": pct(
                        [
                            f["status"]
                            in ("RECRUITING", "ACTIVE_NOT_RECRUITING", "NOT_YET_RECRUITING", "ENROLLING_BY_INVITATION")
                            for f in tr
                        ]
                    ),
                    "n_completed_due": len(due),
                    "results_posted_among_due_pct": pct([f["has_results"] for f in due]),
                    "registered_within_12mo_of_start_pct": pct([timely(r, feats[r["nct_id"]]) for r in sel]),
                }
            )
    write("supplementary/ktrial_characteristics.csv", ch)


if __name__ == "__main__":
    main()
    print("analysis/ktrial_descriptives.py: complete")
