"Derive prior non-K leadership covariates and aggregate K-trial audits."

import csv
import json
from collections import Counter

from config import DATA_DIR, RESULTS_DIR
from outcomes.leadership import QUAL

OUT = RESULTS_DIR


(OUT / "supplementary").mkdir(parents=True, exist_ok=True)


def T(v):
    return v == "True"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    pa = {r["blind_id"]: r for r in csv.DictReader((DATA_DIR / "contemporaneous" / "person_analysis.csv").open())}
    var = {
        r["blind_id"]: r for r in csv.DictReader((DATA_DIR / "instrument" / "analysis" / "person_variants.csv").open())
    }
    extended = {
        r["blind_id"]: r for r in csv.DictReader((DATA_DIR / "derived" / "contemporaneous_extended.csv").open())
    }
    pairs = {}
    for r in csv.DictReader((DATA_DIR / "instrument" / "instrument_pair_outcomes.csv").open()):
        pairs.setdefault(r["blind_id"], []).append(r)
    kt, pk = ([], [])
    for m in ("K23", "K08"):
        req = [
            b
            for b, r in pa.items()
            if r["mechanism"] == m
            and r["group"] == "Required"
            and (r["eligible_main"] == "1")
            and (var[b]["unresolved"] == "0")
        ]
        c = Counter()
        for b in req:
            if extended[b]["ktrial_direct"] == "1":
                continue
            ps = pairs.get(b, [])
            same = [p for p in ps if p["identity"] == "same_person" and T(p["name_guard"])]
            kish = [p for p in same if p["k_link"] != "none" or p["k_relationship"] == "original_K"]
            if any(p["role"] in QUAL and p["window"] == "pre_K" for p in kish):
                c["K trial registered, started before K start"] += 1
            elif any(p["role"] in QUAL and p["scope"] != "applied" for p in kish):
                c["K trial registered as PI, judged basic experimental"] += 1
            elif kish:
                c["K trial registered, awardee not listed as PI"] += 1
            elif any(T(p["primary_pair"]) for p in ps):
                c["no K trial found; led another new trial"] += 1
            elif any(p["k_link"] != "none" for p in ps):
                c["K-linked record, awardee not identified"] += 1
            else:
                c["no K trial found in the registry"] += 1
        n0 = len(req) - sum(extended[b]["ktrial_direct"] == "1" for b in req)
        kt += [
            {"mechanism": m, "n_required": len(req), "n_without_k_trial": n0, "category": k, "n": v}
            for k, v in c.most_common()
        ]
        for g in ("Required", "Not Allowed"):
            grp = [
                b
                for b, r in pa.items()
                if r["mechanism"] == m
                and r["group"] == g
                and (r["eligible_main"] == "1")
                and (var[b]["unresolved"] == "0")
            ]
            prior = [b for b in grp if var[b]["preK_PI"] == "1"]
            ktrial_prior = [
                b
                for b in prior
                if any(
                    T(p["preK_pair"]) and (p["k_link"] != "none" or p["k_relationship"] == "original_K")
                    for p in pairs.get(b, [])
                )
            ]
            only = [
                b
                for b in ktrial_prior
                if all(
                    p["k_link"] != "none" or p["k_relationship"] == "original_K" for p in pairs[b] if T(p["preK_pair"])
                )
            ]
            pk.append(
                {
                    "mechanism": m,
                    "group": g,
                    "n": len(grp),
                    "prior_trial_PI": len(prior),
                    "prior_trial_is_K_trial": len(ktrial_prior),
                    "prior_trial_only_K_trial": len(only),
                    "prior_trial_PI_excluding_K_trial_pct": round(100 * (len(prior) - len(only)) / len(grp), 1),
                }
            )
    for name, rows in (("supplementary/ktrial_audit.csv", kt), ("supplementary/prior_trial_audit.csv", pk)):
        with (OUT / name).open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
            w.writeheader()
            w.writerows(rows)
            print("CSV rows:", len(rows))

    def kish(link, rel):
        return link != "none" or rel == "original_K"

    rows = [
        {
            "blind_id": b,
            "preK_PI_nonK": int(
                any(T(p["preK_pair"]) and (not kish(p["k_link"], p["k_relationship"])) for p in pairs.get(b, []))
            ),
        }
        for b in pa
    ]
    bscreen = {r["case_id"]: r["k_link"] for r in csv.DictReader((DATA_DIR / "historical" / "pairs.csv").open())}
    lab = {
        q.stem: json.loads(q.read_text())["label"]["k_relationship"]
        for q in (DATA_DIR / "historical" / "leadership_labels").glob("*.json")
    }
    bp = {}
    for r in csv.DictReader((DATA_DIR / "historical" / "pair_outcomes.csv").open()):
        bp.setdefault(r["blind_id"], []).append(r)
    hrows = [
        {
            "blind_id": r["blind_id"],
            "preK_PI_nonK": int(
                any(
                    T(p["preK_pair"]) and (not kish(bscreen[p["case_id"]], lab.get(p["case_id"], "")))
                    for p in bp.get(r["blind_id"], [])
                )
            ),
        }
        for r in csv.DictReader((DATA_DIR / "historical" / "person_analysis.csv").open())
    ]
    for name, rs in (("contemporaneous_prior_trials.csv", rows), ("historical_prior_trials.csv", hrows)):
        with (DATA_DIR / "derived" / name).open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["blind_id", "preK_PI_nonK"], lineterminator="\n")
            w.writeheader()
            w.writerows(rs)
            print("CSV rows:", len(rs))


if __name__ == "__main__":
    main()
    print("outcomes/prior_trial_audit.py: complete")
