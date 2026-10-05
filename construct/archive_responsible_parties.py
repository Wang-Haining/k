"""Archive responsible parties."""

import csv
import hashlib
import json
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path

from config import DATA_DIR
from construct.linkage import followup_window, linkage_screen
from construct.registry import leadership, name_terms, norm
from construct.reporter import dump

F = DATA_DIR / "contemporaneous"
R = F / "sources"
path = R / "AACT_20240927_responsible_parties.txt"
cohort = json.loads((F / "cohort_key_private.json").read_text())
key = {r["pi_id"]: r for r in cohort}
assert len(key) == len(cohort) == 1527, "Required source invariant failed; inspect the private input locally."
old = json.loads((F / "archive_candidate_retrieval.json").read_text())
old_leads = {(r["pi_id"], r["nct_id"]): r for r in old["new_leads"]}
surname = defaultdict(set)
hits = defaultdict(list)
type_counts = Counter()
for r in cohort:
    for token in norm(r["last_name"]).split():
        surname[token].add(r["pi_id"])
with path.open() as f:
    for number, row in enumerate(csv.DictReader(f, delimiter="|"), 1):
        assert None not in row and row["nct_id"], "Required source invariant failed; inspect the private input locally."
        role = row["responsible_party_type"].upper().replace("-", "_").replace(" ", "_")
        type_counts[role] += 1
        if role not in ["PRINCIPAL_INVESTIGATOR", "SPONSOR_INVESTIGATOR"] or not row["name"]:
            continue
        tokens = set(norm(row["name"]).split())
        candidates = set().union(*(surname[t] for t in tokens if t in surname))
        p = {
            "identificationModule": {},
            "contactsLocationsModule": {
                "overallOfficials": [{"name": row["name"], "affiliation": row["affiliation"], "role": role}]
            },
        }
        for pi in candidates:
            screen = linkage_screen(key[pi], p)
            if screen != "retrieved_surname_only_without_person_or_project_support":
                hits[pi, row["nct_id"]].append(
                    {"table": "responsible_parties", "record_number": number, "screen": screen, "raw": row}
                )
print("2024 RP SCANNED", "candidate pairs", len(hits), flush=True)
wanted = {n for _, n in hits}
raw_pairs = set()
review_pairs = set()
current = {}
used_sources = set()


def remember(s, source):
    p = s["protocolSection"]
    identity = p["identificationModule"]
    n = identity["nctId"]
    ids = ({n} | set(identity.get("nctIdAliases", []))) & wanted
    for requested in ids:
        status = p.get("statusModule", {})
        date = status.get("lastUpdatePostDateStruct", {}).get("date")
        record = {
            "source_file": str(source),
            "canonical_nct_id": n,
            "explicit_nct_id_aliases": identity.get("nctIdAliases", []),
            "study_type": p.get("designModule", {}).get("studyType"),
            "start_date": status.get("startDateStruct", {}).get("date"),
            "start_date_type": status.get("startDateStruct", {}).get("type"),
            "last_update_posted": date,
            "leadership_entries": leadership(p),
            "identification_module": identity,
        }
        if requested not in current or (date or "") > (current[requested]["last_update_posted"] or ""):
            current[requested] = record
            used_sources.add(str(source))


for r in cohort:
    source = R / f"ct_person_{r['pi_id']}.json"
    saved = json.loads(source.read_text())
    assert saved["status"] == "complete", "Required source invariant failed; inspect the private input locally."
    for s in saved["studies"]:
        raw_pairs.add((r["pi_id"], s["protocolSection"]["identificationModule"]["nctId"]))
        remember(s, source)
blinds = {r["blind_id"]: r["pi_id"] for r in cohort}
for r in json.loads((F / "review_cases.json").read_text()):
    n = r["protocol"]["identificationModule"]["nctId"]
    review_pairs.add((blinds[r["blind_id"]], n))
    p = dict(r["protocol"], contactsLocationsModule={"overallOfficials": r["leadership_entries"]})
    remember({"protocolSection": p}, F / "review_cases.json")
for r in old["new_leads"]:
    n = r["nct_id"]
    record = r["current_record"]
    if n in wanted and record and (n not in current):
        current[n] = dict(record, canonical_nct_id=n, explicit_nct_id_aliases=[])
progress_path = F / "archive_current_fetch_progress.json"
progress = json.loads(progress_path.read_text()) if progress_path.exists() else {"sources": [], "complete": False}
for source in progress["sources"]:
    for s in json.loads(Path(source).read_text())["response"]["studies"]:
        remember(s, source)
missing = wanted - set(current)
for source in sorted(R.glob("ct_full_*.json")) + sorted(R.glob("publication_NCT_*.json")):
    for s in json.loads(source.read_text())["response"].get("studies", []):
        identity = s["protocolSection"]["identificationModule"]
        if ({identity["nctId"]} | set(identity.get("nctIdAliases", []))) & missing:
            remember(s, source)
new = []
for (pi, n), evidence in sorted(hits.items()):
    if (pi, n) in raw_pairs or (pi, n) in review_pairs:
        continue
    r = key[pi]
    given = {w for s in name_terms(r) for w in norm(s).split() if len(w) > 1}
    words = [
        w
        for w in norm(r["institution"]).split()
        if w
        not in {
            "university",
            "college",
            "medicine",
            "medical",
            "school",
            "hospital",
            "institute",
            "research",
            "center",
            "of",
            "the",
            "at",
            "and",
            "for",
            "inc",
        }
    ]
    assert words, "Required source invariant failed; inspect the private input locally."
    strongest = max(words, key=len)
    full = any(given & set(norm(e["raw"]["name"]).split()) for e in evidence)
    strict_inst = any(strongest in norm(e["raw"]["affiliation"]).split() for e in evidence)
    record = current.get(n)
    date = record["start_date"] if record else None
    screen = (
        {
            "study_type": record["study_type"],
            "interventional": None if not record["study_type"] else record["study_type"].upper() == "INTERVENTIONAL",
            "start_date": date,
            "window": followup_window(r["start_date"], r["end_5y"], date),
        }
        if record
        else None
    )
    new.append(
        {
            "pi_id": pi,
            "blind_id": r["blind_id"],
            "name": r["name"],
            "nct_id": n,
            "K_start": r["start_date"],
            "end_5y": r["end_5y"],
            "current_query_compatible": full or strict_inst,
            "full_given_name_token_match": full,
            "original_query_institution_word": strongest,
            "original_query_institution_word_found_in_affiliation": strict_inst,
            "wider_linkage_screen_institution_lead": any(
                e["screen"] == "surname_and_institution_lead" for e in evidence
            ),
            "in_current_full_raw_pair": False,
            "in_review_cases": False,
            "also_in_2022_new_leads": (pi, n) in old_leads,
            "archive2022_screen_if_available": old_leads[pi, n]["archive_screen"] if (pi, n) in old_leads else None,
            "archive2024_study_type_and_start_date": None,
            "archive2024_metadata_status": "not_in_supplied_responsible_parties_table",
            "archive_evidence": evidence,
            "current_record": record,
            "current_screen": screen,
            "current_record_status": "local_copy_found" if record else "local_copy_missing_coordinator_fetch_needed",
            "identity_PI_and_outcome_not_assessed": True,
        }
    )
people = []
for r in cohort:
    pairs = {pair for pair in hits if pair[0] == r["pi_id"]}
    rows = [a for a in new if a["pi_id"] == r["pi_id"]]
    people.append(
        {
            "pi_id": r["pi_id"],
            "blind_id": r["blind_id"],
            "status": "complete",
            "archive_candidate_pairs": len(pairs),
            "new_pairs_absent_raw_and_review": len(rows),
            "current_query_compatible_new_pairs": sum(a["current_query_compatible"] for a in rows),
        }
    )
compatible = [r for r in new if r["current_query_compatible"]]
additional = [r for r in compatible if not r["also_in_2022_new_leads"]]
summary = {
    "people_searched": len(people),
    "rows_scanned": number,
    "archive_candidate_pairs": len(hits),
    "new_pairs_absent_raw_and_review": len(new),
    "new_query_compatible_pairs": len(compatible),
    "new_query_compatible_additional_to_2022_pairs": len(additional),
    "new_query_compatible_current_screen_counts": dict(
        Counter(
            str(r["current_screen"]["interventional"]) + "|" + r["current_screen"]["window"]
            if r["current_screen"]
            else "local_copy_missing"
            for r in compatible
        )
    ),
    "new_query_compatible_additional_current_screen_counts": dict(
        Counter(
            str(r["current_screen"]["interventional"]) + "|" + r["current_screen"]["window"]
            if r["current_screen"]
            else "local_copy_missing"
            for r in additional
        )
    ),
    "missing_query_compatible_current_unique_trials": len({r["nct_id"] for r in compatible if not r["current_record"]}),
}
assert len(people) == 1527 and sum(r["new_pairs_absent_raw_and_review"] for r in people) == len(new), (
    "Required source invariant failed; inspect the private input locally."
)
meta = json.loads((F / "aact_responsible_parties_manifest.json").read_text())
md5 = hashlib.md5(path.read_bytes()).hexdigest()
assert md5 == meta["file_md5"], "Required source invariant failed; inspect the private input locally."
result = {
    "created_at": datetime.now(UTC).isoformat(),
    "source": str(path),
    "source_md5": md5,
    "snapshot_date": "2024-09-27",
    "source_metadata": {
        k: meta[k]
        for k in ["source_record", "download_url", "claimed_snapshot_date", "deposit_date", "published_md5_verified"]
    },
    "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    "source_role_counts": dict(type_counts),
    "current_fetch_progress_when_read": progress,
    "current_record_source_files": sorted(used_sources),
    "summary": summary,
    "people": people,
    "new_leads": new,
    "query_compatible_missing_current_trial_ids": sorted({r["nct_id"] for r in compatible if not r["current_record"]}),
    "additional_to_2022_query_compatible_missing_current_trial_ids": sorted(
        {r["nct_id"] for r in additional if not r["current_record"]}
    ),
    "interpretation": (
        "Uniform source-only 2024 RP named-role pass across all 1527, retaining broa"
        "d linkage_screen leads with original-query-compatible flags. Responsible-pa"
        "rty enums normalized only for matching. No grant table, study type, or star"
        "t date supplied in this snapshot; current and 2022 metadata kept distinct. "
        "No identity, PI, or outcome claims; no external API calls; no 2022 artifact"
        " or review cases altered."
    ),
}
result["missing_current_trial_ids"] = sorted({r["nct_id"] for r in new if not r["current_record"]})
for row in new:
    row["literal_original_query_role_field"] = (
        "responsibleParties; original institution query used AREA[OverallOfficialName]"
    )
    row["role_field_scope_note"] = (
        "RP surname plus exact original institution word is a conceptual query-compa"
        "tible lead under the authorized historical responsible-party recovery, with"
        " the role-field difference explicit."
    )
result["input_sha256"] = {
    "cohort_key_private.json": old["provenance"]["input_sha256"]["cohort_key_private.json"],
    "review_cases.json_at_retrieval": old["provenance"]["input_sha256"]["review_cases.json"],
    "archive_candidate_retrieval.json": hashlib.sha256(
        (F / "archive_candidate_retrieval.json").read_bytes()
    ).hexdigest(),
}
dump(F / "archive_2024_candidate_retrieval.json", result)
print("responsible-party candidate leads:", len(new), flush=True)
