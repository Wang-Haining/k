"""Seven year packets."""

import csv
import json

from config import DATA_DIR
from outcomes.leadership import name_compatible

HD = DATA_DIR / "historical"
RETRIEVAL = "2026-09-27"


def plus7(d):
    return d.replace(d[:4], str(int(d[:4]) + 7), 1)


def main():
    key = {
        r["blind_id"]: r
        for f in (DATA_DIR / "contemporaneous/cohort_key_private.json", HD / "cohort_key_private.json")
        for r in json.loads(f.read_text())
    }
    persons = {r["blind_id"] for r in csv.DictReader((HD / "person_analysis.csv").open())}
    want = {}
    for r in csv.DictReader((HD / "pairs.csv").open()):
        b = r["blind_id"]
        if (
            b in persons
            and r["window"] == "after_5y"
            and (r["study_type"] == "INTERVENTIONAL")
            and (plus7(key[b]["start_date"]) <= RETRIEVAL)
            and r["start_date"]
            and (r["start_date"][:10] <= plus7(key[b]["start_date"]))
        ):
            want[r["case_id"]] = b
    n = 0
    with (HD / "packets.jsonl").open() as f, (HD / "seven_year_packets.jsonl").open("w") as out:
        for line in f:
            p = json.loads(line)
            b = want.get(p["case_id"])
            if b and name_compatible(key[b]["first_name"], key[b]["last_name"], p):
                out.write(line)
                n += 1
    print(len(want), "year 5-7 interventional candidates;", "pass the name guard -> seven_year_packets.jsonl")


if __name__ == "__main__":
    main()
