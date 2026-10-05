"Aggregate registry-history execution fields and institution-bootstrap contrasts."

import csv
import json
import os
import random
from collections import defaultdict

from config import ANALYSIS_SEED, DATA_DIR, RESULTS_DIR
from outcomes.leadership import name_compatible
from outcomes.reporting import stratum

INSTRUMENT_DIR, HD, RV, OUT = (
    DATA_DIR / "instrument",
    DATA_DIR / "historical",
    DATA_DIR / "derived",
    RESULTS_DIR,
)
STARTED = ("RECRUITING", "ENROLLING_BY_INVITATION", "ACTIVE_NOT_RECRUITING", "COMPLETED")


(OUT / "registry_panel").mkdir(parents=True, exist_ok=True)


def is_awardee(name, first, last):
    pk = {
        "trial": {"overall_officials": [{"name": name}], "responsible_party": {}},
        "historical_registry_snapshots": [],
        "protocol_excerpts": [],
    }
    return name_compatible(first, last, pk)


def record_fields(r, h, feats, pubs):
    f = feats.get(r["nct"], {})
    if not h or not h["ev"]:
        return {"cat": "d_insufficient"}
    v0 = h["ev"][0]
    names0 = [n[2:] for n in v0[2]]
    aw0 = any(is_awardee(n, r["first"], r["last"]) for n in names0)
    other0 = any(not is_awardee(n, r["first"], r["last"]) for n in names0)
    later = [e for e in h["ev"][1:] if any(is_awardee(n[2:], r["first"], r["last"]) for n in e[2])]
    kl0, kl_later = (bool(v0[3]), any(e[3] for e in h["ev"][1:]))
    if not names0:
        cat = "d_insufficient"
    elif aw0 and kl0:
        cat = "a_pi_from_registration"
    elif aw0:
        cat = "b_link_added_later_or_never"
    elif other0 and later:
        cat = "c_responsibility_shift"
    else:
        cat = "d_insufficient"

    def au(a):
        return is_awardee(f"{a.get('fore', '')} {a.get('last', '')}", r["first"], r["last"]) if a else False

    pl = pubs.get(r["nct"], [])
    enrol = f.get("enrollment") or 0
    return {
        "cat": cat,
        "v0_awardee_pi": int(aw0),
        "other_pi_v0": int(other0),
        "awardee_added_later": int(not aw0 and bool(later)),
        "klink_v0": int(kl0),
        "klink_added_later": int(not kl0 and kl_later),
        "prospective": int(
            bool(f.get("first_submitted")) and f.get("first_submitted", "9")[:10] <= (r.get("start") or "0")[:10]
        )
        if r.get("start")
        else 0,
        "started": int(bool(h.get("rec")) or (f.get("enrollment_type") == "ACTUAL" and enrol > 0)),
        "completed": int(f.get("status") == "COMPLETED"),
        "completed_within_5y": int(
            f.get("status") == "COMPLETED"
            and bool(f.get("primary_completion"))
            and (f["primary_completion"][:10] <= r["kstart5"])
        ),
        "stopped": int(f.get("status") in ("TERMINATED", "WITHDRAWN")),
        "results": int(bool(f.get("has_results"))),
        "published": int(bool(pl)),
        "awardee_first_last": int(any(au(p.get("first")) or au(p.get("last")) for p in pl)),
    }


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    pa = {r["blind_id"]: r for r in csv.DictReader((HD / "person_analysis.csv").open())}
    extended = {r["blind_id"]: r for r in csv.DictReader((RV / "historical_extended.csv").open())}
    if os.environ.get("PUBLIC") != "1":
        feats = json.loads((INSTRUMENT_DIR / "trial_features.json").read_text())
        hist = json.loads((RV / "ktrial_history.json").read_text())
        pubs = json.loads((RV / "ktrial_pubmed.json").read_text())
        starts = {
            (r["blind_id"], r["nct_id"]): r["start_date"]
            for r in csv.DictReader((RV / "ktrial_pairs.csv").open())
            if r["analysis"] == "historical"
        }
        rows = json.loads((RV / "ktrial_panel_input_private.json").read_text())
        key = {
            k["blind_id"]: k["start_date"]
            for f in (DATA_DIR / "contemporaneous" / "cohort_key_private.json", HD / "cohort_key_private.json")
            for k in json.loads(f.read_text())
        }
        recs = []
        for r in rows:
            r["start"] = starts.get((r["blind_id"], r["nct"]), "")
            ks = key[r["blind_id"]]
            r["kstart5"] = ks.replace(ks[:4], str(int(ks[:4]) + 5), 1)
            recs.append(
                {
                    "blind_id": r["blind_id"],
                    "nct_id": r["nct"],
                    "window": r["window"],
                    **record_fields(r, hist.get(r["nct"]), feats, pubs),
                }
            )
    ids = [
        b
        for b in pa
        if pa[b]["mechanism"] == "K23" and pa[b]["intent"] == "1" and (extended[b]["besh_only_classifier"] == "0")
    ]
    cats = ["a_pi_from_registration", "b_link_added_later_or_never", "c_responsibility_shift", "d_insufficient"]
    flags = [
        "v0_awardee_pi",
        "other_pi_v0",
        "awardee_added_later",
        "klink_v0",
        "klink_added_later",
        "started",
        "completed",
        "completed_within_5y",
        "stopped",
        "results",
        "published",
        "awardee_first_last",
    ]

    if os.environ.get("PUBLIC") == "1":
        P = {
            r["blind_id"]: {k: int(r[k]) for k in ["has_k_trial", *cats, *flags]}
            for r in csv.DictReader((RV / "ktrial_panel_awardees.csv").open())
        }
        assert set(P) == set(ids), "public panel awardee mismatch"
    else:
        by = defaultdict(list)
        for x in recs:
            if x["window"] == "inside":
                by[x["blind_id"]].append(x)

        def person(b):
            xs = by.get(b, [])
            d = {"has_k_trial": int(bool(xs))}
            d.update({c: int(any(x["cat"] == c for x in xs)) for c in cats})
            d.update({k: int(any(x.get(k, 0) for x in xs)) for k in flags})
            return d

        P = {b: person(b) for b in ids}
    S = {b: stratum(pa[b]) for b in ids}
    keys = ["has_k_trial"] + cats + flags
    shares = []
    for s in ("pre_early", "pre_legacy", "post"):
        g = [b for b in ids if S[b] == s]
        shares.append(
            {
                "stratum": s,
                "n_intent_awardees": len(g),
                **{k: round(100 * sum(P[b][k] for b in g) / len(g), 1) for k in keys},
            }
        )
    org = defaultdict(list)
    if os.environ.get("PUBLIC") != "1":
        for b in ids:
            org[pa[b]["org_id"]].append(b)
    ok_, rng = (list(org), random.Random(ANALYSIS_SEED))

    def diff(sample, k, ref):
        a = [P[b][k] for b in sample if S[b] == "post"]
        c = [P[b][k] for b in sample if S[b] == ref]
        return 100 * (sum(a) / len(a) - sum(c) / len(c)) if a and c else float("nan")

    draws = defaultdict(list)
    for _ in range(0 if os.environ.get("PUBLIC") == "1" else 1000):
        smp = [b for _ in ok_ for b in org[rng.choice(ok_)]]
        for k in keys:
            for ref in ("pre_early", "pre_legacy"):
                draws[k, ref].append(diff(smp, k, ref))

    def q(xs, a):
        return sorted(x for x in xs if x == x)[int(a * (sum(1 for x in xs if x == x) - 1))]

    diffs = [
        {
            "quantity": k,
            "comparison": f"post minus {ref}",
            "estimate": round(diff(ids, k, ref), 1),
            **(
                {"lo": round(q(draws[k, ref], 0.025), 1), "hi": round(q(draws[k, ref], 0.975), 1)}
                if os.environ.get("PUBLIC") != "1"
                else {}
            ),
        }
        for k in keys
        for ref in ("pre_early", "pre_legacy")
    ]
    for name, data in (("registry_panel/shares.csv", shares), ("registry_panel/differences.csv", diffs)):
        with (OUT / name).open("w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(data[0]), lineterminator="\n")
            w.writeheader()
            w.writerows(data)
            print("CSV rows:", len(data))
    if os.environ.get("PUBLIC") != "1":
        with (RV / "ktrial_panel_records_private.csv").open("w", newline="") as fh:
            cols = ["blind_id", "nct_id", "window", "cat"] + flags + ["prospective"]
            w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore", lineterminator="\n")
            w.writeheader()
            w.writerows(recs)
            print("CSV rows:", len(recs))


if __name__ == "__main__":
    main()
    print("analysis/leadership_panel.py: complete")
