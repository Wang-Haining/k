"""Archive candidates."""

import csv
import hashlib
import io
import json
import re
import zipfile
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path

from config import DATA_DIR
from construct.linkage import followup_window, linkage_screen
from construct.registry import leadership, name_terms, norm, serial
from construct.reporter import dump

F = DATA_DIR / "contemporaneous"
R = F / "sources"
archive = R / "AACT-2022-11-09.zip"
csv.field_size_limit(2**31 - 1)
cohort = json.loads((F / "cohort_key_private.json").read_text())
assert len(cohort) == 1527 and len({r["pi_id"] for r in cohort}) == 1527, (
    "Required source invariant failed; inspect the private input locally."
)
byid = {r["pi_id"]: r for r in cohort}
surname = defaultdict(set)
grants = defaultdict(set)
for r in cohort:
    assert name_terms(r) and r["last_name"] and r["institution"], (
        "Required source invariant failed; inspect the private input locally."
    )
    for token in norm(r["last_name"]).split():
        surname[token].add(r["pi_id"])
    assert re.fullmatch("K\\d\\d[A-Z]{2}\\d{6}", r["core_project_num"]), (
        "Required source invariant failed; inspect the private input locally."
    )
    grants[serial(r)].add(r["pi_id"])


def array_items(path):
    decoder = json.JSONDecoder()
    buffer = ""
    started = False
    ended = False
    with path.open() as f:
        while chunk := f.read(1024 * 1024):
            buffer += chunk
            while True:
                buffer = buffer.lstrip()
                if not started:
                    assert buffer.startswith("["), (
                        "Required source invariant failed; inspect the private input locally."
                    )
                    buffer = buffer[1:]
                    started = True
                buffer = buffer.lstrip()
                if buffer.startswith(","):
                    buffer = buffer[1:].lstrip()
                if buffer.startswith("]"):
                    assert not buffer[1:].strip(), (
                        "Required source invariant failed; inspect the private input locally."
                    )
                    buffer = ""
                    ended = True
                    break
                if not buffer:
                    break
                try:
                    item, end = decoder.raw_decode(buffer)
                except json.JSONDecodeError:
                    break
                yield item
                buffer = buffer[end:]
    assert started and ended and (not buffer.strip()), (
        "Required source invariant failed; inspect the private input locally."
    )


def digest(path, algorithm="sha256"):
    h = hashlib.new(algorithm)
    with Path(path).open("rb") as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


wanted = set()
hits = defaultdict(list)
table_counts = {}
studies = {}
members = []
with zipfile.ZipFile(archive) as z:
    for table in ["overall_officials", "responsible_parties", "id_information", "studies"]:
        member = f"AACT-2022-11-09/{table}.txt"
        info = z.getinfo(member)
        members.append({"member": member, "bytes": info.file_size, "CRC": info.CRC})
        with z.open(member) as source:
            rows = csv.DictReader(io.TextIOWrapper(source, encoding="utf-8"), delimiter="|")
            count = 0
            for count, row in enumerate(rows, 1):
                assert None not in row and row["nct_id"], (
                    "Required source invariant failed; inspect the private input locally."
                )
                if table == "studies":
                    if row["nct_id"] in wanted:
                        assert row["nct_id"] not in studies, (
                            "Required source invariant failed; inspect the private input locally."
                        )
                        studies[row["nct_id"]] = {"record_number": count, "row": row}
                    continue
                matches = {}
                if table == "id_information":
                    compact = re.sub("[^A-Z0-9]", "", row["id_value"].upper())
                    for match in re.finditer("(?<![A-Z])(?:K\\d\\d)?[A-Z]{2}\\d{6}(?!\\d)", compact):
                        for pi in grants.get(match.group()[-8:], []):
                            matches[pi] = {
                                "screen": "index_grant_lead",
                                "matched_identifier": match.group(),
                                "identifier_match": "complete_K_core"
                                if byid[pi]["core_project_num"] in match.group()
                                else "complete_IC_and_serial",
                                "not_role_proof": True,
                            }
                else:
                    role = row["role"] if table == "overall_officials" else row["responsible_party_type"]
                    if table == "responsible_parties" and role not in [
                        "Principal Investigator",
                        "Sponsor-Investigator",
                    ]:
                        continue
                    tokens = set(norm(row["name"]).split())
                    candidates = set().union(*(surname[t] for t in tokens if t in surname))
                    official = {"name": row["name"], "affiliation": row["affiliation"], "role": role}
                    protocol = {"identificationModule": {}, "contactsLocationsModule": {"overallOfficials": [official]}}
                    for pi in candidates:
                        screen = linkage_screen(byid[pi], protocol)
                        if screen != "retrieved_surname_only_without_person_or_project_support":
                            matches[pi] = {"screen": screen, "not_identity_adjudication": True}
                for pi, match in matches.items():
                    hits[pi, row["nct_id"]].append(dict(match, table=table, record_number=count, raw=row))
        table_counts[table] = count
        wanted = {n for _, n in hits}
        print("ARCHIVE TABLE", "candidate pairs", len(hits), flush=True)
assert set(studies) == wanted, "Required source invariant failed; inspect the private input locally."
raw_pairs = set()
merged_pairs = set()
review_pairs = set()
current = {}
source_files = []


def current_record(study, path):
    p = study["protocolSection"]
    n = p["identificationModule"]["nctId"]
    if n not in wanted:
        return
    status = p.get("statusModule", {})
    date = status.get("lastUpdatePostDateStruct", {}).get("date")
    record = {
        "source_file": str(path.relative_to(F)),
        "study_type": p.get("designModule", {}).get("studyType"),
        "start_date": status.get("startDateStruct", {}).get("date"),
        "start_date_type": status.get("startDateStruct", {}).get("type"),
        "last_update_posted": date,
        "leadership_entries": leadership(p),
        "identification_module": p["identificationModule"],
    }
    if n not in current or (date or "") > (current[n]["last_update_posted"] or ""):
        current[n] = record


for r in cohort:
    path = R / f"ct_person_{r['pi_id']}.json"
    saved = json.loads(path.read_text())
    assert saved["pi_id"] == r["pi_id"] and saved["status"] == "complete", (
        "Required source invariant failed; inspect the private input locally."
    )
    source_files.append({"path": str(path.relative_to(F)), "sha256": digest(path)})
    for s in saved["studies"]:
        raw_pairs.add((r["pi_id"], s["protocolSection"]["identificationModule"]["nctId"]))
        current_record(s, path)
for item in array_items(F / "trials_merged.json"):
    assert item["pi_id"] in byid, "Required source invariant failed; inspect the private input locally."
    for s in item["studies"]:
        merged_pairs.add((item["pi_id"], s["protocolSection"]["identificationModule"]["nctId"]))
        current_record(s, F / "trials_merged.json")
blind_to_pi = {r["blind_id"]: r["pi_id"] for r in cohort}
for row in array_items(F / "review_cases.json"):
    review_pairs.add((blind_to_pi[row["blind_id"]], row["protocol"]["identificationModule"]["nctId"]))
missing = wanted - set(current)
if missing:
    for path in sorted(R.glob("ct_full_*.json")) + sorted(R.glob("publication_NCT_*.json")):
        saved = json.loads(path.read_text())
        for s in saved["response"].get("studies", []):
            if s["protocolSection"]["identificationModule"]["nctId"] in missing:
                current_record(s, path)


def screen(r, study_type, date):
    return {
        "study_type": study_type or None,
        "start_date": date or None,
        "window": followup_window(r["start_date"], r["end_5y"], date),
        "interventional": None if not study_type else study_type.upper() == "INTERVENTIONAL",
    }


new = []
people = []
for (pi, n), evidence in sorted(hits.items()):
    if (pi, n) in raw_pairs or (pi, n) in review_pairs:
        continue
    r = byid[pi]
    old = studies[n]["row"]
    text = old["start_month_year"]
    date = None
    if text:
        fmt = "%B %d, %Y" if "," in text else "%B %Y" if " " in text else "%Y"
        date = datetime.strptime(text, fmt).strftime("%Y-%m-%d" if "," in text else "%Y-%m" if " " in text else "%Y")
    historic = screen(r, old["study_type"], date)
    historic["start_date_precision_source"] = "start_month_year" if text else "missing_original_date_precision"
    record = current.get(n)
    now = screen(r, record["study_type"], record["start_date"]) if record else None
    new.append(
        {
            "pi_id": pi,
            "blind_id": r["blind_id"],
            "name": r["name"],
            "nct_id": n,
            "K_start": r["start_date"],
            "end_5y": r["end_5y"],
            "in_current_full_raw_pair": False,
            "in_trials_merged_pair": (pi, n) in merged_pairs,
            "in_review_cases": False,
            "archive_screen": historic,
            "current_screen": now,
            "current_record_status": "local_copy_found" if record else "local_copy_missing_coordinator_fetch_needed",
            "archive_evidence": evidence,
            "archive_study_evidence": studies[n],
            "current_record": record,
            "review_candidate_archive_inside": historic["interventional"] is True and historic["window"] == "inside",
            "review_candidate_current_inside": now is not None
            and now["interventional"] is True
            and (now["window"] == "inside"),
            "outcome_not_assessed": True,
            "identity_and_role_require_review": True,
        }
    )
for r in cohort:
    pairs = {pair for pair in hits if pair[0] == r["pi_id"]}
    people.append(
        {
            "pi_id": r["pi_id"],
            "blind_id": r["blind_id"],
            "status": "complete",
            "tables_searched": list(table_counts),
            "archive_candidate_pairs": len(pairs),
            "already_current_full_raw_pairs": len(pairs & raw_pairs),
            "already_review_cases": len(pairs & review_pairs),
            "new_pairs_absent_raw_and_review": len(pairs - raw_pairs - review_pairs),
        }
    )
assert len(people) == 1527 and sum(p["archive_candidate_pairs"] for p in people) == len(hits), (
    "Required source invariant failed; inspect the private input locally."
)
assert sum(p["new_pairs_absent_raw_and_review"] for p in people) == len(new), (
    "Required source invariant failed; inspect the private input locally."
)
inventory = json.loads((F / "AACT_20221109_archive_inventory.json").read_text())
md5 = digest(archive, "md5")
assert md5 == inventory["md5"], "Required source invariant failed; inspect the private input locally."
summary = {
    "people_searched": len(people),
    "table_rows_scanned": table_counts,
    "archive_candidate_pairs": len(hits),
    "archive_candidate_people": len({pi for pi, _ in hits}),
    "current_full_raw_pairs": len(raw_pairs),
    "current_merged_pairs": len(merged_pairs),
    "current_review_pairs": len(review_pairs),
    "new_pairs_absent_raw_and_review": len(new),
    "new_unique_trials": len({r["nct_id"] for r in new}),
    "new_pairs_also_absent_merged": sum(not r["in_trials_merged_pair"] for r in new),
    "new_archive_inside_interventional": sum(r["review_candidate_archive_inside"] for r in new),
    "new_current_inside_interventional": sum(r["review_candidate_current_inside"] for r in new),
    "new_archive_screen_counts": dict(
        Counter(str(r["archive_screen"]["interventional"]) + "|" + r["archive_screen"]["window"] for r in new)
    ),
    "new_current_record_status_counts": dict(Counter(r["current_record_status"] for r in new)),
    "new_current_screen_counts": dict(
        Counter(
            str(r["current_screen"]["interventional"]) + "|" + r["current_screen"]["window"]
            if r["current_screen"]
            else "local_copy_missing"
            for r in new
        )
    ),
}
provenance = {
    "created_at": datetime.now(UTC).isoformat(),
    "script_sha256": digest(__file__),
    "archive_file": str(archive.relative_to(F)),
    "archive_md5": md5,
    "archive_inventory": inventory,
    "tables": members,
    "input_sha256": {
        name: digest(F / name)
        for name in [
            "cohort_key_private.json",
            "trials_merged.json",
            "review_cases.json",
            "AACT_20221109_archive_inventory.json",
        ]
    },
    "current_person_files": source_files,
    "method": (
        "All 1527 people searched uniformly; existing linkage_screen given-name/init"
        "ial/surname/institution criteria on historical named role entries; complete"
        " K core or IC plus six-digit serial in id_information only; grant leads are"
        " not role evidence. Inclusive followup_window applied with original archive"
        " date precision. Current FULL raw pairs mean ct_person files; merged pairs "
        "additionally include publication leads. No outcome labels read or assigned;"
        " no API calls. One 2022 archive snapshot cannot establish complete historic"
        "al recall."
    ),
}
dump(
    F / "archive_candidate_retrieval.json",
    {
        "provenance": provenance,
        "summary": summary,
        "people": people,
        "new_leads": new,
        "missing_current_trial_ids": sorted({r["nct_id"] for r in new if r["current_record"] is None}),
    },
)
print("archive candidate leads:", len(new), flush=True)
