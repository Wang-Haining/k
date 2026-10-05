"Combine symmetric registry-only labels and rules into private awardee outcomes."

import csv
import json
import sys
from datetime import date
from pathlib import Path

from config import DATA_DIR
from outcomes.dates import interval
from outcomes.leadership import QUAL, name_compatible

HD = DATA_DIR / "historical"


def years_after(start, k_start):
    return (date.fromisoformat(interval(start)[0]) - date.fromisoformat(k_start)).days / 365.25


def funding(key, raw):
    out = {r["pi_id"]: {"R01": 0, "R34": 0, "U01": 0} for r in key}
    by = {r["pi_id"]: r for r in key}
    for f in raw:
        if f["activity_code"] not in ("R01", "R34", "U01") or f["project_num_split"]["appl_type_code"] != "1":
            continue
        for p in f["principal_investigators"]:
            r = by.get(p["profile_id"])
            if r and r["start_date"] <= f["project_start_date"][:10] <= r["end_5y"]:
                out[r["pi_id"]][f["activity_code"]] = 1
    return out


def main(pair_dir, intent_dir):
    post = json.loads((DATA_DIR / "contemporaneous" / "cohort_key_private.json").read_text())
    pre = json.loads((HD / "cohort_key_private.json").read_text())
    for r in post:
        r["period"] = "post_policy"
    key = post + pre
    fund = funding(post, json.loads((DATA_DIR / "cohort" / "funding_raw.json").read_text()))
    fund.update(funding(pre, json.loads((HD / "funding_raw.json").read_text())))
    names = {r["blind_id"]: r for r in key}
    pairs = {r["case_id"]: r for r in csv.DictReader((HD / "pairs.csv").open())}
    by, pair_rows = ({}, [])
    for line in (HD / "packets.jsonl").open():
        p = json.loads(line)
        cid, s = (p["case_id"], pairs[p["case_id"]])
        k = names[s["blind_id"]]
        if s["qwen_reviewed"] == "True":
            rec = json.loads((Path(pair_dir) / f"{cid}.json").read_text())
            assert rec["status"] == "success" and rec["packet_sha256"] == p["packet_sha256"], cid
            label = rec["label"]
        else:
            assert not name_compatible(k["first_name"], k["last_name"], p) or s["window"] == "after_5y", cid
            label = {
                "identity": "not_named",
                "role": "not_named",
                "scope": "applied",
                "k_relationship": "not_applicable",
            }
        qual = (
            label["identity"] == "same_person"
            and name_compatible(k["first_name"], k["last_name"], p)
            and (label["role"] in QUAL)
        )
        applied = qual and label["scope"] == "applied" and (s["study_type"] == "INTERVENTIONAL")
        sec = applied and s["window"] == "inside"
        pri = sec and s["k_link"] == "none" and (label["k_relationship"] == "new_protocol")
        pair_rows.append(
            {
                "case_id": cid,
                "blind_id": s["blind_id"],
                "secondary_pair": sec,
                "primary_pair": pri,
                "preK_pair": applied and s["window"] == "pre_K",
            }
        )
        by.setdefault(s["blind_id"], []).append(
            {
                "sec": sec,
                "pri": pri,
                "preK": applied and s["window"] == "pre_K",
                "fdaaa": s["fdaaa_like"] == "True",
                "wz": s["flag_withdrawn_zero"] == "True",
                "t": years_after(s["start_date"], k["start_date"]) if sec else None,
            }
        )
    intent = {p.stem: json.loads(p.read_text())["label"] for p in Path(intent_dir).glob("*.json")}
    rows = []
    for r in key:
        ps = by.get(r["blind_id"], [])
        pri = [x for x in ps if x["pri"]]
        f = fund[r["pi_id"]]
        rows.append(
            {
                "blind_id": r["blind_id"],
                "period": r["period"],
                "post": int(r["period"] == "post_policy"),
                "mechanism": r["mechanism"],
                "nofo": r["nofo"],
                "group": r.get("group", ""),
                "year": r["year"],
                "ic": r["ic"],
                "org_id": r["org_id"],
                "intent": int(intent[r["blind_id"]]["research_type"] == "own_trial_planned"),
                "intent_label": intent[r["blind_id"]]["research_type"],
                "primary": int(bool(pri)),
                "secondary": int(any(x["sec"] for x in ps)),
                "primary_fdaaa": int(any(x["fdaaa"] for x in pri)),
                "primary_4y": int(any(x["t"] <= 4 for x in pri)),
                "primary_excl_withdrawn": int(any(not x["wz"] for x in pri)),
                "preK_PI": int(any(x["preK"] for x in ps)),
                "R01": f["R01"],
                "R34": f["R34"],
                "U01": f["U01"],
                "any_funding": int(any(f.values())),
            }
        )
    with (HD / "person_analysis.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
        print("CSV rows:", len(rows))
    with (HD / "pair_outcomes.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(pair_rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(pair_rows)
        print("CSV rows:", len(pair_rows))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
    print("outcomes/historical.py: complete")
