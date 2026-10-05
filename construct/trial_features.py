"""Trial features."""

import json
import re

from config import DATA_DIR

PILOT = re.compile("\\b(pilot|feasibility|feasible|acceptability|preliminary)\\b", re.I)


def features(s):
    ps = s["protocolSection"]
    d, st, ident = (ps.get("designModule", {}), ps.get("statusModule", {}), ps["identificationModule"])
    enroll = d.get("enrollmentInfo", {})
    title = f"{ident.get('briefTitle', '')} {ident.get('officialTitle', '')}"
    return {
        "enrollment": enroll.get("count"),
        "enrollment_type": enroll.get("type", ""),
        "randomized": d.get("designInfo", {}).get("allocation") == "RANDOMIZED",
        "phases": d.get("phases", []),
        "status": st.get("overallStatus", ""),
        "has_results": bool(s.get("hasResults")),
        "primary_completion": st.get("primaryCompletionDateStruct", {}).get("date", ""),
        "pilot_in_title": bool(PILOT.search(title)),
        "intervention_types": sorted(
            {i.get("type", "") for i in ps.get("armsInterventionsModule", {}).get("interventions", [])}
        ),
        "n_sites": len(
            {
                (line.get("facility", ""), line.get("city", ""))
                for line in ps.get("contactsLocationsModule", {}).get("locations", [])
            }
        ),
        "lead_sponsor_class": ps.get("sponsorCollaboratorsModule", {}).get("leadSponsor", {}).get("class", ""),
        "collaborator_classes": sorted(
            {c.get("class", "") for c in ps.get("sponsorCollaboratorsModule", {}).get("collaborators", [])}
        ),
        "nih_grant_ids": sorted({x.get("id", "") for x in ident.get("secondaryIdInfos", []) if x.get("type") == "NIH"}),
        "first_submitted": st.get("studyFirstSubmitDate", ""),
        "results_first_submitted": st.get("resultsFirstSubmitDate", ""),
    }


def main():
    out = {}
    for person in json.loads((DATA_DIR / "contemporaneous/trials_merged.json").read_text()):
        for s in person["studies"]:
            out.setdefault(s["protocolSection"]["identificationModule"]["nctId"], features(s))
    for f in (DATA_DIR / "contemporaneous/sources").glob("ct_person_*.json"):
        for s in json.loads(f.read_text())["studies"]:
            out.setdefault(s["protocolSection"]["identificationModule"]["nctId"], features(s))
    for f in (DATA_DIR / "registry/historical").glob("ct_person_*.json"):
        for s in json.loads(f.read_text())["studies"]:
            out.setdefault(s["protocolSection"]["identificationModule"]["nctId"], features(s))
    (DATA_DIR / "instrument/trial_features.json").write_text(json.dumps(out))
    print(len(out), "NCTs with design features")


if __name__ == "__main__":
    main()
