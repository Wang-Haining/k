"""Retrieve funding inventories and build dated investigator funding events."""

import json

from config import DATA_DIR
from construct.reporter import dump, reporter

CODES = ["R01", "R23", "R29", "R37", "R56", "RF1", "RL1", "U01", "DP1", "DP2", "DP5", "R35", "R61", "R33", "UG3", "UH3"]


def main():
    post = json.loads((DATA_DIR / "contemporaneous/cohort_key_private.json").read_text())
    pre = json.loads((DATA_DIR / "historical/cohort_key_private.json").read_text())
    for name, key, start, label in (
        ("cohort", post, "2018-01-01", "funding"),
        ("historical", pre, "2014-01-01", "hist_funding"),
    ):
        ids = [
            r["pi_id"]
            for r in (sorted(key, key=lambda r: (r["start_date"], r["appl_id"])) if name == "cohort" else key)
        ]
        records = []
        for i in range(0, len(ids), 100):
            records += reporter(
                f"{label}_{i}",
                {
                    "pi_profile_ids": ids[i : i + 100],
                    "activity_codes": ["R01", "U01", "R34"],
                    "project_num_split": {"appl_type_code": "1"},
                    "fiscal_years": [],
                    "project_start_date": {"from_date": start, "to_date": "2026-09-27"},
                },
                DATA_DIR / ("sources/reporter" if name == "cohort" else "sources/historical_reporter"),
            )
        dump(DATA_DIR / name / "funding_raw.json", records)
    key = post + pre
    by = {r["pi_id"]: r for r in key}
    ids = list(by)
    for name, codes, label in (
        ("r01eq", ["R01", "R37", "R35", "DP2"], "r01eq"),
        ("funding", ["R01", "R37", "R35", "DP2", "R61", "R33", "UG3", "UH3"], "funding"),
        ("nih_funding", CODES, "nih_funding"),
    ):
        records = []
        for i in range(0, len(ids), 100):
            records += reporter(
                f"{label}_{i:04d}",
                {
                    "pi_profile_ids": ids[i : i + 100],
                    "activity_codes": codes,
                    "project_num_split": {"appl_type_code": "1"},
                    "fiscal_years": [],
                    "project_start_date": {"from_date": "2014-01-01", "to_date": "2026-09-27"},
                },
                DATA_DIR / "sources" / name,
            )
        events = {r["blind_id"]: [] for r in key}
        indicators = {r["blind_id"]: {"R01eq": 0, "R01eq_contact_PI": 0, "codes": []} for r in key}
        for record in records:
            if record["activity_code"] not in codes or record["project_num_split"]["appl_type_code"] != "1":
                continue
            for pi in record["principal_investigators"]:
                person = by.get(pi["profile_id"])
                start = record["project_start_date"][:10]
                if not person or start < person["start_date"]:
                    continue
                event = {"code": record["activity_code"], "start": start, "contact": bool(pi.get("is_contact_pi"))}
                if name == "nih_funding":
                    event["ic"] = (record.get("core_project_num") or "")[3:5]
                events[person["blind_id"]].append(event)
                if start <= person["end_5y"]:
                    row = indicators[person["blind_id"]]
                    row["R01eq"] = 1
                    row["R01eq_contact_PI"] |= int(bool(pi.get("is_contact_pi")))
                    row["codes"].append(record["activity_code"])
        if name == "r01eq":
            dump(DATA_DIR / "instrument/r01eq_person.json", indicators)
        else:
            dump(DATA_DIR / "derived" / f"{name}_events.json", events)
        print("funding capture:", name, "records:", len(records), "events:", sum(map(len, events.values())))


if __name__ == "__main__":
    main()
