"""Select initial K08/K23 awards and assign stable pseudonymous keys."""

import hashlib
import random

from config import COHORT_SEED, DATA_DIR
from construct.reporter import dump, reporter, table

MAP = {}
for mech, yes, no in [
    ("K08", ["PA-18-372", "PA-19-116", "PA-20-202"], ["PA-18-373", "PA-19-117", "PA-20-203"]),
    ("K23", ["PA-18-374", "PA-19-118", "PA-20-206"], ["PA-18-375", "PA-19-119", "PA-20-205"]),
]:
    for group, codes in [("Required", yes), ("Not Allowed", no)]:
        for code in codes:
            MAP[code] = (mech, group)
HISTORICAL_ANNOUNCEMENTS = {
    "PA-11-193": "K08",
    "PA-14-046": "K08",
    "PA-16-191": "K08",
    "PA-11-194": "K23",
    "PA-14-049": "K23",
    "PA-16-198": "K23",
}


def select_contemporaneous(awards):
    assert awards, "Cohort source failed the announcement, investigator or award-date invariant."
    cohort = []
    excluded = []
    for r in awards:
        assert r["activity_code"] in ["K08", "K23"] and r["project_num_split"]["appl_type_code"] == "1", (
            "Cohort source failed the announcement, investigator or award-date invariant."
        )
        start = r["project_start_date"][:10]
        assert "2018-01-01" <= start <= "2021-09-27", (
            "Cohort source failed the announcement, investigator or award-date invariant."
        )
        if r["opportunity_number"] not in MAP:
            excluded.append(
                {
                    "appl_id": r["appl_id"],
                    "core_project_num": r["core_project_num"],
                    "opportunity_number": r["opportunity_number"],
                    "reason": "outside selected parent NOFOs",
                }
            )
            continue
        assert len(r["principal_investigators"]) == 1, (
            "Cohort source failed the announcement, investigator or award-date invariant."
        )
        pi = r["principal_investigators"][0]
        mech, group = MAP[r["opportunity_number"]]
        assert (
            pi["profile_id"] and pi["first_name"] and pi["last_name"] and r["abstract_text"] and r["agency_ic_admin"]
        ), "Cohort source failed the announcement, investigator or award-date invariant."
        assert mech == r["activity_code"], (
            "Cohort source failed the announcement, investigator or award-date invariant."
        )
        cohort.append(
            {
                "pi_id": pi["profile_id"],
                "name": pi["full_name"],
                "first_name": pi["first_name"],
                "last_name": pi["last_name"],
                "mechanism": mech,
                "group": group,
                "core_project_num": r["core_project_num"],
                "project_num": r["project_num"],
                "appl_id": r["appl_id"],
                "nofo": r["opportunity_number"],
                "start_date": start,
                "end_5y": str(int(start[:4]) + 5) + start[4:],
                "year": int(start[:4]),
                "ic": r["agency_ic_admin"]["abbreviation"],
                "institution": r["organization"]["org_name"],
                "org_id": r["organization"]["external_org_id"],
                "title": r["project_title"],
                "abstract": r["abstract_text"],
                "source": r["project_detail_url"],
            }
        )
    cohort.sort(key=lambda r: (r["start_date"], r["appl_id"]))
    seen = set()
    unique = []
    for r in cohort:
        if r["pi_id"] in seen:
            excluded.append(
                {
                    "appl_id": r["appl_id"],
                    "core_project_num": r["core_project_num"],
                    "opportunity_number": r["nofo"],
                    "reason": "later initial K award for same PI in window",
                }
            )
        else:
            unique.append(r)
            seen.add(r["pi_id"])
    cohort = unique
    assert len({r["core_project_num"] for r in cohort}) == len(cohort), (
        "Cohort source failed the announcement, investigator or award-date invariant."
    )
    return (cohort, excluded)


def select_historical(awards, post_ids):
    cohort, excluded = ([], [])
    for r in awards:
        nofo = r["opportunity_number"]
        if nofo not in HISTORICAL_ANNOUNCEMENTS:
            if r["project_start_date"][:10] < "2018-01-01":
                excluded.append(
                    {
                        "appl_id": r["appl_id"],
                        "core_project_num": r["core_project_num"],
                        "opportunity_number": nofo,
                        "reason": "not a selected historical parent announcement",
                    }
                )
            continue
        if HISTORICAL_ANNOUNCEMENTS[nofo] != r["activity_code"]:
            excluded.append(
                {
                    "appl_id": r["appl_id"],
                    "core_project_num": r["core_project_num"],
                    "opportunity_number": nofo,
                    "reason": "activity code does not match FOA",
                }
            )
            continue
        pis = r["principal_investigators"] or []
        if len(pis) != 1 or not r.get("abstract_text"):
            excluded.append(
                {
                    "appl_id": r["appl_id"],
                    "core_project_num": r["core_project_num"],
                    "opportunity_number": nofo,
                    "reason": "not single PI or no abstract",
                }
            )
            continue
        pi, start = (pis[0], r["project_start_date"][:10])
        cohort.append(
            {
                "pi_id": pi["profile_id"],
                "name": pi["full_name"],
                "first_name": pi["first_name"],
                "last_name": pi["last_name"],
                "mechanism": r["activity_code"],
                "period": "pre_policy",
                "core_project_num": r["core_project_num"],
                "project_num": r["project_num"],
                "appl_id": r["appl_id"],
                "nofo": nofo,
                "start_date": start,
                "end_5y": str(int(start[:4]) + 5) + start[4:],
                "year": int(start[:4]),
                "ic": r["agency_ic_admin"]["abbreviation"],
                "institution": r["organization"]["org_name"],
                "org_id": r["organization"]["external_org_id"],
                "title": r["project_title"],
                "abstract": r["abstract_text"],
                "source": r["project_detail_url"],
            }
        )
    cohort.sort(key=lambda r: (r["start_date"], r["appl_id"]))
    seen, unique = (set(), [])
    for r in cohort:
        reason = (
            "later initial K award for same PI"
            if r["pi_id"] in seen
            else "PI also in post-policy cohort"
            if r["pi_id"] in post_ids
            else None
        )
        if reason:
            excluded.append(
                {
                    "appl_id": r["appl_id"],
                    "core_project_num": r["core_project_num"],
                    "opportunity_number": r["nofo"],
                    "reason": reason,
                }
            )
        else:
            unique.append(r)
            seen.add(r["pi_id"])
    for i, r in enumerate(unique, 1):
        r["blind_id"] = f"H{i:04d}"
    return (unique, excluded)


def assign_ids(cohort):
    rng = random.Random(COHORT_SEED)
    sample = []
    for mechanism in ("K08", "K23"):
        for group in ("Required", "Not Allowed"):
            pool = sorted(
                [r for r in cohort if r["mechanism"] == mechanism and r["group"] == group], key=lambda r: r["pi_id"]
            )
            sample.extend(rng.sample(pool, min(20, len(pool))))
    rng.shuffle(sample)
    ids = {r["pi_id"]: f"P{i:03}" for i, r in enumerate(sample, 1)}
    remaining = sorted(
        [r for r in cohort if r["pi_id"] not in ids], key=lambda r: hashlib.sha256(str(r["pi_id"]).encode()).hexdigest()
    )
    ids.update({r["pi_id"]: f"P{i:04d}" for i, r in enumerate(remaining, len(sample) + 1)})
    assert len(ids) == len(set(ids.values())) == len(cohort), "Nonunique cohort keys"
    return sorted([dict(r, blind_id=ids[r["pi_id"]]) for r in cohort], key=lambda r: r["blind_id"])


def main():
    awards = reporter(
        "k_inventory",
        {
            "activity_codes": ["K08", "K23"],
            "project_num_split": {"appl_type_code": "1"},
            "project_start_date": {"from_date": "2018-01-01", "to_date": "2021-09-27"},
            "fiscal_years": [],
        },
    )
    post, excluded = select_contemporaneous(awards)
    dump(DATA_DIR / "cohort/cohort.json", post)
    ids = [r["pi_id"] for r in post]
    history = []
    for i in range(0, len(ids), 100):
        history += reporter(
            f"k_history_{i}",
            {
                "pi_profile_ids": ids[i : i + 100],
                "activity_codes": ["K08", "K23"],
                "project_num_split": {"appl_type_code": "1"},
                "fiscal_years": [],
                "project_start_date": {"from_date": "1985-01-01", "to_date": "2021-09-27"},
            },
        )
    by = {r["pi_id"]: r for r in post}
    prior = sum(
        1
        for award in history
        for pi in award["principal_investigators"]
        if pi["profile_id"] in by and award["project_start_date"][:10] < by[pi["profile_id"]]["start_date"]
    )
    assert prior == 0, f"Expected no prior initial K08/K23 awards, got {prior}"
    dump(DATA_DIR / "cohort/k_history.json", history)
    post = assign_ids(post)
    sample = [r for r in post if int(r["blind_id"][1:]) <= 80]
    dump(DATA_DIR / "cohort/sample_key_private.json", sample)
    dump(DATA_DIR / "contemporaneous/cohort_key_private.json", post)
    table(DATA_DIR / "contemporaneous/excluded.csv", excluded)
    awards = []
    for mechanism in ("K08", "K23"):
        awards += reporter(
            f"hist_inventory_{mechanism}",
            {
                "activity_codes": [mechanism],
                "project_num_split": {"appl_type_code": "1"},
                "project_start_date": {"from_date": "2014-01-01", "to_date": "2021-09-27"},
                "fiscal_years": [],
            },
            DATA_DIR / "sources/historical_reporter",
        )
    pre, excluded = select_historical(awards, {r["pi_id"] for r in post})
    dump(DATA_DIR / "historical/cohort_key_private.json", pre)
    table(DATA_DIR / "historical/excluded.csv", excluded)
    print("cohort keys:", len(post), "contemporaneous;", len(pre), "historical")


if __name__ == "__main__":
    main()
