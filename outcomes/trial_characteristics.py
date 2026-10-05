"Derive private trial-characteristic outcomes and first-event person-years."

import csv
import json

from config import DATA_DIR

INSTRUMENT_DIR = DATA_DIR / "instrument"
OUT = DATA_DIR / "derived"
DUE = "2025-09-27"


def informative(f):
    return f["randomized"] and ((f["enrollment"] or 0) >= 100 or f["n_sites"] >= 3)


def extra(pairs, nct_of, start_of, feats, persons, r01eq):
    by = {}
    for r in pairs:
        by.setdefault(r["blind_id"], []).append(r)
    rows = []
    for b in persons:
        rs = by.get(b, [])
        pri = [(r, feats[nct_of[r["case_id"]]]) for r in rs if r["primary_pair"] == "True"]
        ktrial = [r for r in rs if r["secondary_pair"] == "True" and r["primary_pair"] != "True"]
        rows.append(
            {
                "blind_id": b,
                "first_primary_start": min((start_of[r["case_id"]] for r, _ in pri), default=""),
                "first_secondary_start": min(
                    (start_of[r["case_id"]] for r in rs if r["secondary_pair"] == "True"), default=""
                ),
                "informative_new_trial": int(any((informative(f) for _, f in pri))),
                "multisite_new_trial": int(any((f["n_sites"] >= 3 for _, f in pri))),
                "completed_with_results": int(any((f["status"] == "COMPLETED" and f["has_results"] for _, f in pri))),
                "new_trial_completed_due": int(
                    any(
                        (
                            f["status"] == "COMPLETED" and f["primary_completion"][:10] <= DUE
                            for _, f in pri
                            if f["primary_completion"]
                        )
                    )
                ),
                "nih_funded_new_trial": int(
                    any(
                        (
                            f["nih_grant_ids"] or f["lead_sponsor_class"] == "NIH" or "NIH" in f["collaborator_classes"]
                            for _, f in pri
                        )
                    )
                ),
                "industry_new_trial": int(
                    any(
                        (
                            f["lead_sponsor_class"] == "INDUSTRY" or "INDUSTRY" in f["collaborator_classes"]
                            for _, f in pri
                        )
                    )
                ),
                "k_trial_registered_as_PI": int(bool(ktrial)),
                "R01eq": r01eq[b]["R01eq"],
                "R01eq_contact_PI": r01eq[b]["R01eq_contact_PI"],
            }
        )
    return rows


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    feats = json.loads((INSTRUMENT_DIR / "trial_features.json").read_text())
    r01eq = json.loads((INSTRUMENT_DIR / "r01eq_person.json").read_text())
    main_pairs = list(csv.DictReader((INSTRUMENT_DIR / "instrument_pair_outcomes.csv").open()))
    persons_main = [
        r["blind_id"] for r in csv.DictReader((DATA_DIR / "contemporaneous" / "person_analysis.csv").open())
    ]
    m = extra(
        main_pairs,
        {r["case_id"]: r["nct_id"] for r in main_pairs},
        {r["case_id"]: r["start_date"] for r in main_pairs},
        feats,
        persons_main,
        r01eq,
    )
    bh_screen = {r["case_id"]: r for r in csv.DictReader((DATA_DIR / "historical" / "pairs.csv").open())}
    bh_pairs = list(csv.DictReader((DATA_DIR / "historical" / "pair_outcomes.csv").open()))
    persons_bh = [r["blind_id"] for r in csv.DictReader((DATA_DIR / "historical" / "person_analysis.csv").open())]
    h = extra(
        bh_pairs,
        {c: s["nct_id"] for c, s in bh_screen.items()},
        {c: s["start_date"] for c, s in bh_screen.items()},
        feats,
        persons_bh,
        r01eq,
    )
    for name, rows in (("contemporaneous_characteristics.csv", m), ("historical_characteristics.csv", h)):
        with (OUT / name).open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
            w.writeheader()
            w.writerows(rows)
            print("CSV rows:", len(rows))


if __name__ == "__main__":
    main()


def panel():
    from datetime import date

    from outcomes.dates import interval

    keys = {
        r["blind_id"]: r
        for f in (
            DATA_DIR / "contemporaneous" / "cohort_key_private.json",
            DATA_DIR / "historical" / "cohort_key_private.json",
        )
        for r in json.loads(f.read_text())
    }
    extra_rows = {r["blind_id"]: r for r in csv.DictReader((OUT / "historical_characteristics.csv").open())}
    rows = []
    for b, e in extra_rows.items():
        k0 = date.fromisoformat(keys[b]["start_date"])
        ev = date.fromisoformat(interval(e["first_primary_start"])[0]) if e["first_primary_start"] else None
        for k in range(5):
            lo = k0.replace(year=k0.year + k) if not (k0.month == 2 and k0.day == 29) else date(k0.year + k, 3, 1)
            hi = lo.replace(year=lo.year + 1) if not (lo.month == 2 and lo.day == 29) else date(lo.year + 1, 3, 1)
            event = int(ev is not None and lo <= ev < hi)
            rows.append({"blind_id": b, "k": k, "cal_year": (lo + (hi - lo) / 2).year, "event": event})
            if ev is not None and ev < hi:
                break
    with (OUT / "historical_person_years.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
        print("CSV rows:", len(rows))


if __name__ == "__main__":
    panel()
    print("outcomes/trial_characteristics.py: complete")
