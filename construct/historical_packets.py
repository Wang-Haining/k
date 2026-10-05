"""Historical packets."""

import csv
import hashlib
import io
import json
import re
import zipfile
from collections import defaultdict

from config import DATA_DIR
from construct.linkage import followup_window
from construct.packet_fields import clip
from outcomes.leadership import name_compatible

F, INSTRUMENT, HD = (DATA_DIR / "contemporaneous", DATA_DIR / "instrument", DATA_DIR / "historical")
AACT22 = F / "sources" / "AACT-2022-11-09.zip"
RP24 = F / "sources" / "AACT_20240927_responsible_parties.txt"


def people_sources():
    post = [
        dict(r, period="post_policy", raw=F / "sources" / f"ct_person_{r['pi_id']}.json")
        for r in json.loads((F / "cohort_key_private.json").read_text())
    ]
    pre = [
        dict(r, raw=DATA_DIR / "registry/historical" / f"ct_person_{r['pi_id']}.json")
        for r in json.loads((HD / "cohort_key_private.json").read_text())
    ]
    orgs = {
        r["blind_id"]: r["orgs"]
        for f in (INSTRUMENT / "person_orgs.json", HD / "person_orgs.json")
        for r in json.loads(f.read_text())
    }
    return (post + pre, orgs)


def aact(ncts):
    rows = defaultdict(list)
    with zipfile.ZipFile(AACT22) as z:
        for table, key in (("overall_officials", "role"), ("responsible_parties", "responsible_party_type")):
            name = next(n for n in z.namelist() if n.endswith(f"/{table}.txt"))
            for r in csv.DictReader(io.TextIOWrapper(z.open(name), encoding="utf-8", errors="replace"), delimiter="|"):
                if r["nct_id"] in ncts:
                    rows[r["nct_id"]].append(
                        {
                            "snapshot": "2022-11-09",
                            "table": table,
                            "name": r.get("name", ""),
                            "role": r.get(key, ""),
                            "affiliation": r.get("affiliation") or r.get("organization") or "",
                        }
                    )
    with RP24.open(encoding="utf-8", errors="replace") as fh:
        for r in csv.DictReader(fh, delimiter="|"):
            if r["nct_id"] in ncts:
                rows[r["nct_id"]].append(
                    {
                        "snapshot": "2024-09-27",
                        "table": "responsible_parties",
                        "name": r.get("name", ""),
                        "role": r.get("responsible_party_type", ""),
                        "affiliation": r.get("affiliation") or r.get("organization") or "",
                    }
                )
    return rows


def trial_summary(p):
    ident, design, status = (p["identificationModule"], p.get("designModule", {}), p.get("statusModule", {}))
    sponsor, arms = (p.get("sponsorCollaboratorsModule", {}), p.get("armsInterventionsModule", {}))
    return {
        "nct_id": ident["nctId"],
        "brief_title": ident.get("briefTitle", ""),
        "official_title": clip(ident.get("officialTitle", ""), 300),
        "brief_summary": clip(p.get("descriptionModule", {}).get("briefSummary", ""), 1200),
        "conditions": p.get("conditionsModule", {}).get("conditions", [])[:8],
        "interventions": [f"{i.get('type', '')}: {i.get('name', '')}" for i in arms.get("interventions", [])][:8],
        "study_type": design.get("studyType", ""),
        "primary_purpose": design.get("designInfo", {}).get("primaryPurpose", ""),
        "phases": design.get("phases", []),
        "allocation": design.get("designInfo", {}).get("allocation", ""),
        "start": status.get("startDateStruct", {}),
        "overall_status": status.get("overallStatus", ""),
        "enrollment": design.get("enrollmentInfo", {}),
        "lead_sponsor": sponsor.get("leadSponsor", {}).get("name", ""),
        "responsible_party": {k: v for k, v in sponsor.get("responsibleParty", {}).items() if k != "oldNameTitle"},
        "overall_officials": [
            {k: o.get(k, "") for k in ("name", "affiliation", "role")}
            for o in p.get("contactsLocationsModule", {}).get("overallOfficials", [])
        ],
        "secondary_ids": [f"{s.get('type', '')}:{s.get('id', '')}" for s in ident.get("secondaryIdInfos", [])][:10],
        "org_study_id": ident.get("orgStudyIdInfo", {}).get("id", ""),
    }


def is_fdaaa_like(p):
    types = {i.get("type") for i in p.get("armsInterventionsModule", {}).get("interventions", [])}
    phases = set(p.get("designModule", {}).get("phases", []))
    drug = bool(types & {"DRUG", "BIOLOGICAL", "COMBINATION_PRODUCT", "GENETIC"}) and bool(
        phases & {"PHASE2", "PHASE3", "PHASE4"}
    )
    return drug or "DEVICE" in types


def main():
    people, orgs = people_sources()
    studies, ncts = ({}, set())
    for r in people:
        assert r["raw"].exists(), "Required source invariant failed; inspect the private input locally."
        studies[r["blind_id"]] = [s["protocolSection"] for s in json.loads(r["raw"].read_text())["studies"]]
        ncts |= {p["identificationModule"]["nctId"] for p in studies[r["blind_id"]]}
    hist = aact(ncts)
    HD.mkdir(parents=True, exist_ok=True)
    pairs, n_pk, n_q = ([], 0, 0)
    with (HD / "packets.jsonl").open("w") as f, (HD / "reviewed_packets.jsonl").open("w") as fq:
        for r in sorted(people, key=lambda r: r["blind_id"]):
            serial = re.sub("^K\\d\\d", "", r["core_project_num"]).lower()
            for p in studies[r["blind_id"]]:
                t = trial_summary(p)
                nct = t["nct_id"]
                cid = f"{r['blind_id']}_{nct}"
                packet = {
                    "case_id": cid,
                    "awardee": {
                        "name": r["name"],
                        "K_core_project_num": r["core_project_num"],
                        "K_start": r["start_date"],
                        "K_window_end": r["end_5y"],
                        "K_institution": r["institution"],
                        "NIH_organizations": orgs[r["blind_id"]],
                        "K_title": r["title"],
                        "K_abstract": clip(r["abstract"], 4000),
                    },
                    "trial": t,
                    "historical_registry_snapshots": hist.get(nct, [])[:20],
                    "protocol_excerpts": [],
                }
                packet["packet_sha256"] = hashlib.sha256(json.dumps(packet, sort_keys=True).encode()).hexdigest()
                f.write(json.dumps(packet, ensure_ascii=False) + "\n")
                n_pk += 1
                win = followup_window(r["start_date"], r["end_5y"], t["start"].get("date", ""))
                needs_review = name_compatible(r["first_name"], r["last_name"], packet) and win != "after_5y"
                if needs_review:
                    fq.write(json.dumps(packet, ensure_ascii=False) + "\n")
                    n_q += 1
                enroll = t["enrollment"]
                pairs.append(
                    {
                        "case_id": cid,
                        "blind_id": r["blind_id"],
                        "nct_id": nct,
                        "study_type": t["study_type"],
                        "primary_purpose": t["primary_purpose"],
                        "start_date": t["start"].get("date", ""),
                        "start_type": t["start"].get("type", ""),
                        "window": win,
                        "qwen_reviewed": needs_review,
                        "k_link": "id_field"
                        if serial in re.sub("[^a-z0-9]", "", json.dumps(p["identificationModule"]).lower())
                        else "none",
                        "fdaaa_like": is_fdaaa_like(p),
                        "flag_withdrawn_zero": t["overall_status"] == "WITHDRAWN"
                        and str(enroll.get("count", "")) == "0",
                    }
                )
    with (HD / "pairs.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(pairs[0]))
        w.writeheader()
        w.writerows(pairs)
    with (HD / "persons.csv").open("w", newline="") as fh:
        cols = [
            "blind_id",
            "pi_id",
            "period",
            "mechanism",
            "nofo",
            "group",
            "year",
            "start_date",
            "ic",
            "org_id",
            "first_name",
            "last_name",
        ]
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for r in people:
            w.writerow({k: r.get(k, "") for k in cols})
    print(
        len(people),
        "people;",
        len(pairs),
        "pairs;",
        "packets;",
        "sent to Qwen (name screen);",
        sum(bool(v) for v in hist.values()),
        "NCTs with AACT rows",
    )


if __name__ == "__main__":
    main()
