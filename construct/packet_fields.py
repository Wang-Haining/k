"""Packet fields."""

import hashlib
import json
import re


def clip(s, n):
    s = " ".join((s or "").split())
    return s if len(s) <= n else s[:n] + " [...]"


def trial_block(c, r):
    p = c["protocol"]
    ident, design = (p["identificationModule"], p.get("designModule", {}))
    status, desc = (p.get("statusModule", {}), p.get("descriptionModule", {}))
    arms = p.get("armsInterventionsModule", {})
    sponsor = p.get("sponsorCollaboratorsModule", {})
    block = {
        "case_id": c["case_id"],
        "nct_id": ident["nctId"],
        "brief_title": ident.get("briefTitle", ""),
        "official_title": clip(ident.get("officialTitle", ""), 300),
        "brief_summary": clip(desc.get("briefSummary", ""), 1200),
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
        "screen": {
            "matched_PI_name": r["qualifying_name"],
            "role_source": r["role_source"],
            "affiliation_matches_NIH_orgs": r["affiliation_match"] == "True",
            "k_serial_link": r["k_link"],
        },
        "ask": ["scope"]
        + (["identity"] if r["tierA"] == "pending_identity" else [])
        + (["k_relationship"] if r["pending_krel"] == "True" else []),
    }
    block["evidence_sha256"] = hashlib.sha256(json.dumps(block, sort_keys=True).encode()).hexdigest()
    return block


def mask(text):
    return re.sub(
        "(?i)\\b(?:(?:PA|PAR|PAS)-\\d{2}-\\d{3}|RFA-[A-Z]{2}-\\d{2}-\\d{3})\\b|(?:independent\\s+)?clinical\\s+trials?\\s+(?:not\\s+allowed|required|optional)",
        "[funding designation redacted]",
        text or "",
    )
