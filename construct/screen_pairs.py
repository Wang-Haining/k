"""Screen pairs."""

import csv
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

from config import DATA_DIR
from construct.linkage import followup_window
from construct.registry import norm

RULE_NAME = "name_and_timing"
F, INSTRUMENT = (DATA_DIR / "contemporaneous", DATA_DIR / "instrument")
INPUTS = {
    "review_cases": F / "review_cases.json",
    "historical_addenda": F / "historical_registry_addenda.json",
    "start_conflicts": F / "source_start_conflicts.json",
    "window_corrections": F / "outcome_window_corrections.json",
    "person_orgs": INSTRUMENT / "person_orgs.json",
    "cohort_key": F / "cohort_key_private.json",
    "script": Path(__file__),
}
QUALIFYING = {"PRINCIPAL_INVESTIGATOR", "SPONSOR_INVESTIGATOR"}
AACT_QUALIFYING = {"principal investigator", "sponsor investigator"}
TITLES = {
    "dr",
    "prof",
    "md",
    "phd",
    "mph",
    "ms",
    "msc",
    "mscr",
    "mshp",
    "mhs",
    "mas",
    "rn",
    "np",
    "mbbs",
    "do",
    "pharmd",
    "facs",
    "facp",
    "faap",
    "frcpc",
    "jr",
    "sr",
    "ii",
    "iii",
    "mba",
    "ma",
    "bs",
    "ba",
    "mpp",
    "dsc",
    "dnp",
    "psyd",
}
GENERIC = {
    "university",
    "college",
    "medicine",
    "medical",
    "school",
    "hospital",
    "hospitals",
    "institute",
    "research",
    "center",
    "centre",
    "of",
    "the",
    "at",
    "and",
    "for",
    "inc",
    "health",
    "system",
    "systems",
    "national",
    "state",
    "department",
    "clinic",
    "clinics",
    "sciences",
    "science",
    "foundation",
    "childrens",
    "children",
    "general",
    "regents",
    "trustees",
    "corporation",
    "board",
    "campus",
    "california",
    "new",
    "york",
    "north",
    "south",
}


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def given_names(first):
    return [w for w in norm(first).split() if w]


def name_match(first, last, name):
    tokens = norm(name).split()
    surname = norm(last).split()
    if not surname or not set(surname) <= set(tokens):
        return None
    rest = [w for w in tokens if w not in surname and w not in TITLES]
    given = given_names(first)
    if any(g in rest for g in given if len(g) > 1):
        return "full"
    if rest and given and any(w[0] == given[0][0] for w in rest):
        return "initial"
    return None


def distinctive(org):
    return {w for w in norm(org).split() if w not in GENERIC and len(w) >= 4}


def affiliation_match(orgs, aff):
    words = set(norm(aff or "").split())
    return bool(words) and any(distinctive(o) & words for o in orgs)


def main():
    cases = json.loads(INPUTS["review_cases"].read_text())
    assert len(cases) == 11998, "Required source invariant failed; inspect the private input locally."
    assert not any(k in cases[0] for k in ("group", "funding", "any_funding")), (
        "Required source invariant failed; inspect the private input locally."
    )
    people = [
        {k: r[k] for k in ("blind_id", "first_name", "last_name", "core_project_num", "start_date", "end_5y")}
        for r in json.loads(INPUTS["cohort_key"].read_text())
    ]
    assert len(people) == 1527, "Required source invariant failed; inspect the private input locally."
    orgs = {r["blind_id"]: r["orgs"] for r in json.loads(INPUTS["person_orgs"].read_text())}
    conflicts = json.loads(INPUTS["start_conflicts"].read_text())
    withdrawn_zero = {c["case_id"] for c in conflicts["withdrawn_zero_with_actual_start"]}
    start_conflict = {c["case_id"] for c in conflicts["historical_current_actual_start_window_conflicts"]}
    corrected = {c["case_id"] for c in json.loads(INPUTS["window_corrections"].read_text())}
    aact = defaultdict(list)
    for a in json.loads(INPUTS["historical_addenda"].read_text()):
        rows = json.loads(Path(a["local_text"]).read_text()).get("verbatim_table_rows", {})
        for o in rows.get("overall_officials", []):
            aact[a["nct_id"]].append(
                (a["snapshot_date"], o.get("name", ""), norm(o.get("role", "")), o.get("affiliation", ""))
            )
        for o in rows.get("responsible_parties", []):
            aact[a["nct_id"]].append(
                (
                    a["snapshot_date"],
                    o.get("name", ""),
                    norm(o.get("responsible_party_type") or ""),
                    o.get("affiliation") or o.get("organization") or "",
                )
            )
    pairs = []
    for c in cases:
        p = c["protocol"]
        nct = p["identificationModule"]["nctId"]
        design = p.get("designModule", {})
        status = p.get("statusModule", {})
        start = status.get("startDateStruct", {})
        serial = re.sub("^K\\d\\d", "", c["K_core_project_num"]).lower()

        def flat(o):
            return re.sub("[^a-z0-9]", "", json.dumps(o).lower())

        k_link = "id_field" if serial in flat(p["identificationModule"]) else "text" if serial in flat(p) else "none"
        best, aff, qualifying_name, nonqualifying = (None, False, "", "")
        for o in c["leadership_entries"]:
            m = name_match(c["first_name"], c["last_name"], o["name"])
            if not m:
                continue
            if o.get("role") in QUALIFYING:
                if best != "full":
                    best, qualifying_name = (m, o["name"])
                aff = aff or affiliation_match(orgs[c["blind_id"]], o.get("affiliation", ""))
            else:
                nonqualifying = nonqualifying or o.get("role", "")
        role_source = "current" if best else ""
        aact_hits = [
            (d, n, a)
            for d, n, r, a in aact.get(nct, [])
            if r in AACT_QUALIFYING and name_match(c["first_name"], c["last_name"], n)
        ]
        aact_dates = sorted((d for d, n, a in aact_hits if name_match(c["first_name"], c["last_name"], n) == "full"))
        if not best and aact_hits:
            d, qualifying_name, a = sorted(
                aact_hits, key=lambda h: name_match(c["first_name"], c["last_name"], h[1]) != "full"
            )[0]
            best, role_source = (name_match(c["first_name"], c["last_name"], qualifying_name), "aact_" + d)
            aff = any(affiliation_match(orgs[c["blind_id"]], h[2]) for h in aact_hits)
        pairs.append(
            {
                "case_id": c["case_id"],
                "blind_id": c["blind_id"],
                "nct_id": nct,
                "study_type": design.get("studyType", ""),
                "primary_purpose": design.get("designInfo", {}).get("primaryPurpose", ""),
                "overall_status": status.get("overallStatus", ""),
                "start_date": start.get("date", ""),
                "start_type": start.get("type", ""),
                "window": followup_window(c["K_start"], c["end_5y"], start.get("date", "")),
                "name_match": best or "",
                "affiliation_match": aff,
                "qualifying_name": qualifying_name,
                "role_source": role_source,
                "named_nonqualifying_role": nonqualifying,
                "k_link": k_link,
                "aact_first_named_PI": aact_dates[0] if aact_dates else "",
                "flag_withdrawn_zero": c["case_id"] in withdrawn_zero,
                "flag_start_conflict": c["case_id"] in start_conflict,
                "flag_window_corrected": c["case_id"] in corrected,
            }
        )
    claimants = defaultdict(set)
    for r in pairs:
        if r["name_match"]:
            claimants[r["nct_id"], norm(r["qualifying_name"])].add(r["blind_id"])
    for r in pairs:
        r["collision"] = bool(r["name_match"]) and len(claimants[r["nct_id"], norm(r["qualifying_name"])]) > 1
        if r["name_match"] == "full" and r["affiliation_match"] and (not r["collision"]):
            r["identity"] = "A1_auto"
        elif r["name_match"]:
            r["identity"] = "A2_queue"
        else:
            r["identity"] = "no_named_PI"
        eligible = r["study_type"] == "INTERVENTIONAL"
        if r["identity"] == "no_named_PI" or not eligible:
            r["tierA"] = "not_qualifying"
        elif r["window"] in ("boundary_uncertain", "missing"):
            r["tierA"] = "timing_unresolved"
        elif r["window"] != "inside":
            r["tierA"] = "outside_window"
        elif r["identity"] == "A2_queue":
            r["tierA"] = "pending_identity"
        else:
            r["tierA"] = "qualifying"
        r["pending_krel"] = r["tierA"] in ("qualifying", "pending_identity") and r["k_link"] == "none"
    by_person = defaultdict(list)
    for r in pairs:
        by_person[r["blind_id"]].append(r)
    persons = []
    for person in people:
        rows = by_person.get(person["blind_id"], [])
        q = [r for r in rows if r["tierA"] == "qualifying"]
        pend = [r for r in rows if r["tierA"] == "pending_identity"]
        timing = [r for r in rows if r["tierA"] == "timing_unresolved"]
        if q:
            secondary = "event_A"
        elif pend:
            secondary = "pending_identity"
        elif timing:
            secondary = "timing_unresolved"
        else:
            secondary = "not_documented"
        if any(r["pending_krel"] for r in q + pend):
            primary = "pending_B"
        elif pend:
            primary = "pending_identity"
        elif timing:
            primary = "timing_unresolved"
        else:
            primary = "not_documented"
        preK = [
            r
            for r in rows
            if r["study_type"] == "INTERVENTIONAL" and r["window"] == "pre_K" and (r["identity"] != "no_named_PI")
        ]
        persons.append(
            {
                "blind_id": person["blind_id"],
                "n_candidate_pairs": len(rows),
                "n_qualifying_A1": len(q),
                "n_pending_identity": len(pend),
                "n_timing_unresolved": len(timing),
                "n_k_linked_qualifying": sum(r["k_link"] != "none" for r in q),
                "n_pending_krel": sum(r["pending_krel"] for r in q + pend),
                "secondary_tierA": secondary,
                "primary_tierA": primary,
                "first_qualifying_start": min((r["start_date"] for r in q), default=""),
                "preK_PI_A1": any(r["identity"] == "A1_auto" for r in preK),
                "preK_PI_A2_only": bool(preK) and (not any(r["identity"] == "A1_auto" for r in preK)),
                "needs_B_identity": bool(pend),
                "needs_B_krel": any(r["pending_krel"] for r in q + pend),
            }
        )
    INSTRUMENT.mkdir(exist_ok=True)
    for name, rows in (
        ("pair_screen.csv", sorted(pairs, key=lambda r: r["case_id"])),
        ("person_screen.csv", sorted(persons, key=lambda r: r["blind_id"])),
    ):
        with (INSTRUMENT / name).open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
    summary = {
        "pairs_tierA": dict(sorted(Counter(r["tierA"] for r in pairs).items())),
        "pairs_identity": dict(sorted(Counter(r["identity"] for r in pairs).items())),
        "persons_secondary": dict(sorted(Counter(r["secondary_tierA"] for r in persons).items())),
        "persons_primary": dict(sorted(Counter(r["primary_tierA"] for r in persons).items())),
        "persons_needs_B_identity": sum(r["needs_B_identity"] for r in persons),
        "persons_needs_B_krel": sum(r["needs_B_krel"] for r in persons),
        "persons_needs_B_any": sum(r["needs_B_identity"] or r["needs_B_krel"] for r in persons),
        "pairs_in_B_dossiers": sum(
            r["tierA"] in ("qualifying", "pending_identity") and (r["pending_krel"] or r["tierA"] == "pending_identity")
            for r in pairs
        ),
        "persons_preK_PI_A1": sum(r["preK_PI_A1"] for r in persons),
        "collision_pairs": sum(r["collision"] for r in pairs),
    }
    manifest = {
        "rule_version": RULE_NAME,
        "blinding": "group and funding never read (source fields only)",
        "input_sha256": {k: sha(p) for k, p in INPUTS.items()},
        "summary": summary,
    }
    (INSTRUMENT / "screen_manifest.json").write_text(json.dumps(manifest, indent=2))
    print("screened pairs:", len(pairs), "people:", len(persons))


if __name__ == "__main__":
    sys.exit(main())
