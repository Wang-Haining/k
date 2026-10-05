"""Write the K23 trial-intent K-trial registry-history roster."""

import csv
import json
import re

from config import DATA_DIR
from construct.reporter import dump


def main():
    historical = DATA_DIR / "historical"
    derived = DATA_DIR / "derived"
    people = {r["blind_id"]: r for r in csv.DictReader((historical / "person_analysis.csv").open())}
    extended = {r["blind_id"]: r for r in csv.DictReader((derived / "historical_extended.csv").open())}
    key = {
        r["blind_id"]: r
        for cohort in ("contemporaneous", "historical")
        for r in json.loads((DATA_DIR / cohort / "cohort_key_private.json").read_text())
    }
    rows = []
    for pair in csv.DictReader((derived / "ktrial_pairs.csv").open()):
        if pair["analysis"] != "historical":
            continue
        b = pair["blind_id"]
        if people[b]["mechanism"] != "K23" or people[b]["intent"] != "1" or extended[b]["besh_only_classifier"] != "0":
            continue
        person = key[b]
        rows.append(
            {
                "i": len(rows),
                "blind_id": b,
                "nct": pair["nct_id"],
                "first": person["first_name"],
                "last": person["last_name"],
                "serial": re.sub(r"^K\d\d", "", person["core_project_num"]),
                "window": pair["window"],
            }
        )
    assert rows, "Expected a nonempty K-trial roster"
    assert len({(r["blind_id"], r["nct"]) for r in rows}) == len(rows), "Duplicate roster pairs"
    dump(derived / "ktrial_panel_input_private.json", rows)
    print("K-trial panel roster rows:", len(rows))


if __name__ == "__main__":
    main()
