"Estimate scientific-lineage shares and contrasts from frozen pair ratings."

import csv
import random
import sys
from collections import defaultdict
from pathlib import Path

from config import ANALYSIS_SEED, DATA_DIR, RESULTS_DIR
from outcomes.reporting import stratum

HD, RV, OUT = (DATA_DIR / "historical", DATA_DIR / "derived", RESULTS_DIR)
DEV = {"extension", "same_approach_new_question"}


(OUT / "lineage").mkdir(parents=True, exist_ok=True)


def main(path):
    with Path(path).open() as handle:
        lab = {r["item"]: r["lineage"] for r in csv.DictReader(handle)}
    key = list(csv.DictReader((DATA_DIR / "ratings" / "lineage_sample_private.csv").open()))
    pa = {r["blind_id"]: r for r in csv.DictReader((HD / "person_analysis.csv").open())}
    extended = {r["blind_id"]: r for r in csv.DictReader((RV / "historical_extended.csv").open())}
    ids = [
        b
        for b in pa
        if pa[b]["mechanism"] == "K23" and pa[b]["intent"] == "1" and (extended[b]["besh_only_classifier"] == "0")
    ]
    S = {b: stratum(pa[b]) for b in ids}
    dev, anyl, trials = (defaultdict(int), defaultdict(int), defaultdict(lambda: [0, 0]))
    for k in key:
        b, label = (k["blind_id"], lab[k["item"]])
        anyl[b] = 1
        if label in DEV:
            dev[b] = 1
        if b in S:
            trials[S[b]][0] += label in DEV
            trials[S[b]][1] += 1
    P = {
        b: {"new_trial": anyl[b], "developed_new_trial": dev[b], "other_new_trial_only": int(anyl[b] and (not dev[b]))}
        for b in ids
    }
    org = defaultdict(list)
    for b in ids:
        org[pa[b]["org_id"]].append(b)
    ok, rng = (list(org), random.Random(ANALYSIS_SEED))

    def share(smp, s, k):
        return 100 * sum(P[b][k] for b in smp if S[b] == s) / max(1, sum(1 for b in smp if S[b] == s))

    rows = []
    for k in ("new_trial", "developed_new_trial", "other_new_trial_only"):
        for ref in ("pre_early", "pre_legacy"):
            est = share(ids, "post", k) - share(ids, ref, k)
            d = []
            for _ in range(1000):
                smp = [b for _ in ok for b in org[rng.choice(ok)]]
                d.append(share(smp, "post", k) - share(smp, ref, k))
            d.sort()
            rows.append(
                {
                    "quantity": k,
                    "comparison": f"post minus {ref}",
                    "post_pct": round(share(ids, "post", k), 1),
                    "ref_pct": round(share(ids, ref, k), 1),
                    "difference": round(est, 1),
                    "lo": round(d[24], 1),
                    "hi": round(d[974], 1),
                }
            )
    for s, (a, n) in sorted(trials.items()):
        rows.append(
            {
                "quantity": "share of new trials developed from the K work",
                "comparison": s,
                "post_pct": "",
                "ref_pct": round(100 * a / n, 1),
                "difference": "",
                "lo": "",
                "hi": f"n={n}",
            }
        )
    with (OUT / "lineage/estimates.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
        print("CSV rows:", len(rows))


if __name__ == "__main__":
    main(sys.argv[1])
    print("analysis/lineage.py: complete")
