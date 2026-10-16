"""Trial people."""

import json

from config import DATA_DIR

F, INSTRUMENT = (DATA_DIR / "contemporaneous", DATA_DIR / "instrument")
people = {}
for person in json.loads((F / "trials_merged.json").read_text()):
    for s in person["studies"]:
        ps = s["protocolSection"]
        nct = ps["identificationModule"]["nctId"]
        rec = {
            "overall_officials": [
                {k: o.get(k, "") for k in ("name", "affiliation", "role")}
                for o in ps.get("contactsLocationsModule", {}).get("overallOfficials", [])
            ],
            "responsible_party": {
                k: v
                for k, v in ps.get("sponsorCollaboratorsModule", {}).get("responsibleParty", {}).items()
                if k != "oldNameTitle"
            },
            "lastUpdatePostDate": ps.get("statusModule", {}).get("lastUpdatePostDateStruct", {}).get("date", ""),
        }
        old = people.get(nct)
        if old and old != rec and (len(json.dumps(rec)) <= len(json.dumps(old))):
            continue
        people[nct] = rec
cases = json.loads((F / "review_cases.json").read_text())
need = {c["protocol"]["identificationModule"]["nctId"] for c in cases}
(INSTRUMENT / "trial_people.json").write_text(json.dumps(people, ensure_ascii=False))
print("trial role records:", len(people), "required:", len(need), "missing:", len(need - people.keys()))
