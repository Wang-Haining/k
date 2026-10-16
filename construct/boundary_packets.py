"""Boundary packets."""

import csv
import json
import random

from config import ANALYSIS_SEED, DATA_DIR
from construct.packet_fields import mask

INSTRUMENT, HD, RV = (DATA_DIR / "instrument", DATA_DIR / "historical", DATA_DIR / "derived")
N = {"grant_linked": 20, "judged_only": 15, "new": 20}


def fields(p):
    t = p["trial"]
    return {
        "K_title": p["awardee"]["K_title"],
        "K_abstract": mask(p["awardee"]["K_abstract"] or ""),
        "trial_title": t["official_title"] or t["brief_title"],
        "trial_summary": t["brief_summary"],
        "conditions": "; ".join(t["conditions"] or []),
        "interventions": json.dumps(t["interventions"])[:1500],
        "phases": "; ".join(t["phases"] or []),
        "allocation": t["allocation"],
        "enrollment": t["enrollment"],
    }


def main():
    rng = random.Random(ANALYSIS_SEED)
    pa = {r["blind_id"]: r for r in csv.DictReader((HD / "person_analysis.csv").open())}
    extended = {r["blind_id"]: r for r in csv.DictReader((RV / "historical_extended.csv").open())}

    def ok(b):
        return pa[b]["mechanism"] == "K23" and pa[b]["intent"] == "1" and (extended[b]["besh_only_classifier"] == "0")

    kt = [
        r
        for r in csv.DictReader((RV / "ktrial_pairs.csv").open())
        if r["analysis"] == "historical" and r["window"] == "inside" and ok(r["blind_id"])
    ]
    new = [
        r
        for r in csv.DictReader((HD / "pair_outcomes.csv").open())
        if r["primary_pair"] == "True" and ok(r["blind_id"])
    ]
    pool = {}
    for r in kt:
        pool.setdefault(
            (pa[r["blind_id"]]["period"], "grant_linked" if r["k_grant_linked"] == "1" else "judged_only"), []
        ).append(r["case_id"] if "case_id" in r else f"{r['blind_id']}_{r['nct_id']}")
    for r in new:
        pool.setdefault((pa[r["blind_id"]]["period"], "new"), []).append(r["case_id"])
    picks = []
    for (per, cls), ids in sorted(pool.items()):
        for c in rng.sample(sorted(set(ids)), min(N[cls], len(set(ids)))):
            picks.append(("historical", per, cls, c))
    var = {r["blind_id"]: r for r in csv.DictReader((INSTRUMENT / "analysis" / "person_variants.csv").open())}
    main = {r["blind_id"]: r for r in csv.DictReader((DATA_DIR / "contemporaneous/person_analysis.csv").open())}
    contemporary = {r["blind_id"]: r for r in csv.DictReader((RV / "contemporaneous_extended.csv").open())}
    first = {}
    for r in csv.DictReader((INSTRUMENT / "instrument_pair_outcomes.csv").open()):
        b = r["blind_id"]
        if (
            r["primary_pair"] == "True"
            and main[b]["mechanism"] == "K23"
            and (main[b]["group"] == "Required")
            and (main[b]["eligible_main"] == "1")
            and (var[b]["unresolved"] == "0")
            and (contemporary[b]["ktrial_direct"] == "0")
            and (b not in first or r["start_date"] < first[b]["start_date"])
        ):
            first[b] = r
    picks += [("main", "post_policy", "new_no_ktrial_required", r["case_id"]) for r in first.values()]
    packets = {}
    for f in (HD / "reviewed_packets.jsonl", INSTRUMENT / "qwen" / "packets_all.jsonl"):
        for line in f.open():
            p = json.loads(line)
            packets[p["case_id"]] = p
    rng.shuffle(picks)
    sheet, key = ([], [])
    for i, (an, per, cls, c) in enumerate(picks, 1):
        sheet.append({"item": i, **fields(packets[c]), "k_relationship": "", "reason": ""})
        key.append({"item": i, "analysis": an, "period": per, "instrument_class": cls, "case_id": c})
    for name, rows in (("krel_rater_sheet.csv", sheet), ("krel_sample_private.csv", key)):
        with (DATA_DIR / "ratings" / name).open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
    from collections import Counter

    print(len(sheet), Counter((k["analysis"], k["period"], k["instrument_class"]) for k in key))


if __name__ == "__main__":
    main()
