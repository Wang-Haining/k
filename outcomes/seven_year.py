"Extend private new-trial leadership outcomes through seven years after K start."

import csv
import json

from config import DATA_DIR
from outcomes.extended import timely
from outcomes.leadership import QUAL, name_compatible

HD, RV = (DATA_DIR / "historical", DATA_DIR / "derived")


def main():
    key = {
        r["blind_id"]: r
        for f in (DATA_DIR / "contemporaneous" / "cohort_key_private.json", HD / "cohort_key_private.json")
        for r in json.loads(f.read_text())
    }
    pa = {r["blind_id"]: r for r in csv.DictReader((HD / "person_analysis.csv").open())}
    pairs = {r["case_id"]: r for r in csv.DictReader((HD / "pairs.csv").open())}
    packets = {json.loads(label)["case_id"]: json.loads(label) for label in (HD / "seven_year_packets.jsonl").open()}
    feats = json.loads((DATA_DIR / "instrument" / "trial_features.json").read_text())
    extended = {r["blind_id"]: r for r in csv.DictReader((RV / "historical_extended.csv").open())}
    late, late_timely = (set(), set())
    for f in (HD / "seven_year_labels" / "labels").glob("*.json"):
        rec = json.loads(f.read_text())
        cid = rec["case_id"]
        lab = rec["label"]
        assert rec["status"] == "success" and rec["packet_sha256"] == packets[cid]["packet_sha256"], cid
        s = pairs[cid]
        b = s["blind_id"]
        k = key[b]
        if (
            lab["identity"] == "same_person"
            and name_compatible(k["first_name"], k["last_name"], packets[cid])
            and (lab["role"] in QUAL)
            and (lab["scope"] == "applied")
            and (s["study_type"] == "INTERVENTIONAL")
            and (s["k_link"] == "none")
            and (lab["k_relationship"] == "new_protocol")
        ):
            late.add(b)
            if timely(s, feats[s["nct_id"]]):
                late_timely.add(b)
    rows = []
    for b, p in pa.items():
        ks = key[b]["start_date"]
        if ks.replace(ks[:4], str(int(ks[:4]) + 7), 1) <= "2026-09-27":
            rows.append(
                {
                    "blind_id": b,
                    "new_trial_7y": int(p["primary"] == "1" or b in late),
                    "new_trial_years_5_7_only": int(p["primary"] == "0" and b in late),
                    "new_trial_7y_timely": int(extended[b]["primary_timely"] == "1" or b in late_timely),
                }
            )
    with (RV / "historical_seven_year.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
        print("CSV rows:", len(rows))


if __name__ == "__main__":
    main()
    print("outcomes/seven_year.py: complete")
