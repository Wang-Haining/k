"""Assemble NIH organization histories from investigator project captures."""

import json

from config import DATA_DIR
from construct.reporter import dump, reporter
from outcomes.names import norm


def main():
    for cohort in ("contemporaneous", "historical"):
        key = json.loads((DATA_DIR / cohort / "cohort_key_private.json").read_text())
        ids = [r["pi_id"] for r in key]
        assert len(set(ids)) == len(key), "Duplicate investigator keys"
        orgs = {r["pi_id"]: {norm(r["institution"])} for r in key}
        for i in range(0, len(ids), 50):
            for project in reporter(
                f"orgs_{i:04d}", {"pi_profile_ids": ids[i : i + 50]}, DATA_DIR / "reporter" / cohort
            ):
                name = norm((project.get("organization") or {}).get("org_name") or "")
                for pi in project.get("principal_investigators") or []:
                    if pi["profile_id"] in orgs and name:
                        orgs[pi["profile_id"]].add(name)
        rows = [{"pi_id": r["pi_id"], "blind_id": r["blind_id"], "orgs": sorted(orgs[r["pi_id"]])} for r in key]
        target = "instrument" if cohort == "contemporaneous" else "historical"
        dump(DATA_DIR / target / "person_orgs.json", rows)
        print("organization histories:", cohort, len(rows))


if __name__ == "__main__":
    main()
