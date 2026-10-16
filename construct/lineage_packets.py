"""Lineage packets."""

import csv
import json
import random

from config import ANALYSIS_SEED, DATA_DIR
from construct.boundary_packets import mask

INSTRUMENT, HD, RV = (DATA_DIR / "instrument", DATA_DIR / "historical", DATA_DIR / "derived")


def trial_text(t):
    return {
        "title": t["official_title"] or t["brief_title"],
        "summary": (t["brief_summary"] or "")[:1500],
        "conditions": "; ".join(t["conditions"] or []),
        "interventions": json.dumps(t["interventions"])[:1200],
        "phases": "; ".join(t["phases"] or []),
        "allocation": t["allocation"],
    }


def main():
    pa = {r["blind_id"]: r for r in csv.DictReader((HD / "person_analysis.csv").open())}
    extended = {r["blind_id"]: r for r in csv.DictReader((RV / "historical_extended.csv").open())}

    def ok(b):
        return (
            b in pa
            and pa[b]["mechanism"] == "K23"
            and (pa[b]["intent"] == "1")
            and (extended[b]["besh_only_classifier"] == "0")
        )

    packets = {}
    for line in (HD / "packets.jsonl").open():
        p = json.loads(line)
        if ok(p["case_id"].split("_")[0]):
            packets[p["case_id"]] = p
    ktrial = {}
    for r in csv.DictReader((RV / "ktrial_pairs.csv").open()):
        cid = f"{r['blind_id']}_{r['nct_id']}"
        if (
            r["analysis"] == "historical"
            and ok(r["blind_id"])
            and (cid in packets)
            and (r["blind_id"] not in ktrial or r["start_date"] < ktrial[r["blind_id"]][0])
        ):
            ktrial[r["blind_id"]] = (r["start_date"], cid)
    new = [
        r
        for r in csv.DictReader((HD / "pair_outcomes.csv").open())
        if r["primary_pair"] == "True" and ok(r["blind_id"])
    ]
    rng = random.Random(ANALYSIS_SEED)
    rng.shuffle(new)
    sheet, key = ([], [])
    for i, r in enumerate(new, 1):
        p = packets[r["case_id"]]
        k = packets[ktrial[r["blind_id"]][1]]["trial"] if r["blind_id"] in ktrial else None
        row = {
            "item": i,
            "K_title": mask(p["awardee"]["K_title"]),
            "K_abstract": mask(p["awardee"]["K_abstract"] or ""),
        }
        row.update({f"Ktrial_{a}": trial_text(k)[a] if k else "" for a in ("title", "summary", "interventions")})
        row.update({f"new_{a}": v for a, v in trial_text(p["trial"]).items()})
        row.update({"lineage": "", "reason": ""})
        sheet.append(row)
        key.append(
            {
                "item": i,
                "case_id": r["case_id"],
                "blind_id": r["blind_id"],
                "period": pa[r["blind_id"]]["period"],
                "has_ktrial": int(r["blind_id"] in ktrial),
            }
        )
    for name, rows in (("lineage_rater_sheet.csv", sheet), ("lineage_sample_private.csv", key)):
        with (DATA_DIR / "ratings" / name).open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
    from collections import Counter

    print(len(sheet), "new-trial items;", Counter((k["period"], k["has_ktrial"]) for k in key))


if __name__ == "__main__":
    main()
