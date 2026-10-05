"""Merge candidates."""

import hashlib
import json
import re
import time
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

from config import DATA_DIR
from construct.linkage import linkage_screen, window
from construct.registry import leadership
from construct.reporter import dump

F = DATA_DIR / "contemporaneous"
R = F / "sources"
cohort = json.loads((F / "cohort_key_private.json").read_text())
seed_order = {
    row["pi_id"]: [study["protocolSection"]["identificationModule"]["nctId"] for study in row["studies"]]
    for row in json.loads((F / "trials_merged.json").read_text())
}
assert set(seed_order) == {r["pi_id"] for r in cohort}, "Merged seed must cover every cohort investigator"
assert all(len(ids) == len(set(ids)) for ids in seed_order.values()), "Duplicate trials in the merged seed"
snapshot = json.loads((F / "publication_identity_snapshot.json").read_text())
window_recovery = {
    (r["blind_id"], r["nct_id"])
    for r in json.loads((F / "historical_start_exclusion_audit.json").read_text())["conflicts"]
}
assert all((R / f"ct_person_{r['pi_id']}.json").exists() for r in cohort), (
    "Required source invariant failed; inspect the private input locally."
)
assert (
    hashlib.sha256((F / "publication_all_article_identity_audit.json").read_bytes()).hexdigest()
    == snapshot["publication_audit_sha256"]
), "Required source invariant failed; inspect the private input locally."
audited = {r["blind_id"]: r for r in snapshot["people"]}
key = [r for r in cohort if r["blind_id"] in audited]
assert len(key) == snapshot["audited_people_n"], "Required source invariant failed; inspect the private input locally."
for r in key:
    assert (
        hashlib.sha256((R / f"pubmed_person_{r['pi_id']}.json").read_bytes()).hexdigest()
        == audited[r["blind_id"]]["sha256"]
    ), "Required source invariant failed; inspect the private input locally."
previous = {
    s["protocolSection"]["identificationModule"]["nctId"]: s
    for item in json.loads((DATA_DIR / "cohort/trials_with_sample_search.json").read_text())
    for s in item["studies"]
}
ct = {r["pi_id"]: json.loads((R / f"ct_person_{r['pi_id']}.json").read_text()) for r in key}
pub = {r["pi_id"]: json.loads((R / f"pubmed_person_{r['pi_id']}.json").read_text()) for r in key}
for item in ct.values():
    previous.update({s["protocolSection"]["identificationModule"]["nctId"]: s for s in item["studies"]})
for path in R.glob("publication_NCT_*.json"):
    saved = json.loads(path.read_text())
    previous.update(
        {s["protocolSection"]["identificationModule"]["nctId"]: s for s in saved["response"].get("studies", [])}
    )
archive_leads = [
    r
    for name in ["archive_candidate_retrieval.json", "archive_2024_candidate_retrieval.json"]
    for r in json.loads((F / name).read_text())["new_leads"]
    if r["current_query_compatible"]
]
fetch = json.loads((F / "archive_current_fetch_progress.json").read_text())
assert fetch["complete"], "Required source invariant failed; inspect the private input locally."
archive_source_paths = set(fetch["sources"]) | {
    str((F / r["current_record"]["source_file"]).resolve())
    for r in archive_leads
    if r.get("current_record") and r["current_record"]["identification_module"]["nctId"] not in previous
}
for name in sorted(archive_source_paths):
    saved = json.loads(Path(name).read_text())
    if isinstance(saved, list):
        assert all(isinstance(item, dict) and "studies" in item for item in saved), (
            "Required source invariant failed; inspect the private input locally."
        )
        records = [s for item in saved for s in item["studies"]]
    else:
        records = saved["response"]["studies"] if "response" in saved else saved["studies"]
    for s in records:
        previous.setdefault(s["protocolSection"]["identificationModule"]["nctId"], s)
canonical = {}
for n, s in previous.items():
    for old in [n] + s["protocolSection"]["identificationModule"].get("nctIdAliases", []):
        assert old not in canonical or canonical[old] == n, (
            "Required source invariant failed; inspect the private input locally."
        )
        canonical[old] = n
archive_by_pi = {}
archive_log = []
for lead in archive_leads:
    n = lead["nct_id"]
    assert n in canonical, "Required source invariant failed; inspect the private input locally."
    c = canonical[n]
    archive_by_pi.setdefault(lead["pi_id"], set()).add(c)
    archive_log.append(
        {
            "blind_id": lead["blind_id"],
            "requested_nct_id": n,
            "canonical_nct_id": c,
            "archive_evidence": lead["archive_evidence"],
            "interpretation": "Historical retrieval support only; identity, role and timing need independent review.",
        }
    )
dump(F / "archive_linkage_integration.json", archive_log)
identity = {
    (r["blind_id"], r["pmid"]): r for r in json.loads((F / "publication_all_article_identity_audit.json").read_text())
}
publication_leads = {}
publication_audit = []
body_leads = json.loads((F / "published_protocol_new_leads_audit.json").read_text())
body_leads += json.loads((F / "published_protocol_identifier_new_leads.json").read_text())
assert body_leads and len({(r["blind_id"], r["nct_id"], r["pmid"]) for r in body_leads}) == len(body_leads), (
    "Required source invariant failed; inspect the private input locally."
)
for r in key:
    leads = {}
    for a in pub[r["pi_id"]]["articles"]:
        row = identity[r["blind_id"], a["pmid"]]
        assert row["status"] in ["supported", "explicit_author_conflict", "identity_unresolved"], (
            "Required source invariant failed; inspect the private input locally."
        )
        if not a["ncts"]:
            continue
        publication_audit.append(
            {
                "blind_id": r["blind_id"],
                "pmid": a["pmid"],
                "identity_status": row["status"],
                "ncts": a["ncts"],
                "retained_as_uncertain_or_supported_lead": row["status"] != "explicit_author_conflict",
            }
        )
        if row["status"] == "explicit_author_conflict":
            continue
        for n in a["ncts"]:
            leads.setdefault(n, []).append(
                {
                    "pmid": a["pmid"],
                    "source": "https://pubmed.ncbi.nlm.nih.gov/" + a["pmid"] + "/",
                    "identity_status": row["status"],
                    "author_evidence": row["author_evidence"],
                    "nct_provenance": row["nct_provenance"],
                    "title": a.get("title"),
                    "not_PI_evidence": True,
                }
            )
    articles = {a["pmid"]: a for a in pub[r["pi_id"]]["articles"]}
    for b in body_leads:
        if b["blind_id"] != r["blind_id"]:
            continue
        row = identity[r["blind_id"], b["pmid"]]
        assert row["status"] != "explicit_author_conflict", (
            "Required source invariant failed; inspect the private input locally."
        )
        n = b["nct_id"]
        publication_audit.append(
            {
                "blind_id": r["blind_id"],
                "pmid": b["pmid"],
                "identity_status": row["status"],
                "ncts": [n],
                "retained_as_uncertain_or_supported_lead": True,
                "new_source": "published_protocol_full_text",
                "source_file": b["source"],
            }
        )
        if any(a["pmid"] == b["pmid"] for a in leads.get(n, [])):
            continue
        leads.setdefault(n, []).append(
            {
                "pmid": b["pmid"],
                "source": "https://pubmed.ncbi.nlm.nih.gov/" + b["pmid"] + "/",
                "identity_status": row["status"],
                "author_evidence": row["author_evidence"],
                "nct_provenance": [
                    {
                        "nct_id": n,
                        "full_text_source": b["source"],
                        "note": "NCT outside bibliography; candidate lead, association and PI status require review",
                    }
                ],
                "title": articles[b["pmid"]]["title"],
                "not_PI_evidence": True,
            }
        )
    publication_leads[r["pi_id"]] = leads
dump(F / "publication_linkage_audit.json", publication_audit)
needed = sorted({n for leads in publication_leads.values() for n in leads} - set(previous))
unavailable = []
for i in range(0, len(needed), 50):
    batch = needed[i : i + 50]
    q = " OR ".join(batch)
    path = R / f"publication_NCT_{hashlib.sha256(q.encode()).hexdigest()[:12]}.json"
    if path.exists():
        saved = json.loads(path.read_text())
        assert saved["query"] == q, "Required source invariant failed; inspect the private input locally."
        d = saved["response"]
    else:
        url = "https://clinicaltrials.gov/api/v2/studies?" + urllib.parse.urlencode(
            {"query.id": q, "pageSize": 100, "countTotal": "true"}
        )
        time.sleep(1.2)
        d = json.load(urllib.request.urlopen(url, timeout=90))
        dump(path, {"query": q, "url": url, "retrieved_at": datetime.now(UTC).isoformat(), "response": d})
    assert not d.get("nextPageToken") and len(d.get("studies", [])) == d["totalCount"], (
        "Required source invariant failed; inspect the private input locally."
    )
    got = {s["protocolSection"]["identificationModule"]["nctId"]: s for s in d.get("studies", [])}
    previous.update(got)
    unavailable.extend(
        {"nct_id": n, "status": "not_returned_by_registry_query", "evidence_file": str(path)}
        for n in batch
        if n not in got
    )
    print("PUB NCT FETCH", "/", len(needed), "unavailable", len(unavailable), flush=True)
dump(F / "unavailable_publication_NCTs.json", unavailable)
merged = []
review = []
logs = [
    {
        "pi_id": r["pi_id"],
        "blind_id": r["blind_id"],
        "registry_status": "complete",
        "publication_status": "retrieval_or_identity_audit_pending",
        "n_candidates": None,
    }
    for r in cohort
    if r["blind_id"] not in audited
]
screened = []
for r in key:
    studies = {s["protocolSection"]["identificationModule"]["nctId"]: s for s in ct[r["pi_id"]]["studies"]}
    leads = publication_leads[r["pi_id"]]
    for n in archive_by_pi.get(r["pi_id"], set()):
        studies.setdefault(n, previous[n])
    for n in leads:
        if n in previous:
            studies[n] = previous[n]
    order = seed_order[r["pi_id"]]
    ordered = [n for n in order if n in studies] + sorted(studies.keys() - set(order))
    studies = {n: studies[n] for n in ordered}
    merged.append({"pi_id": r["pi_id"], "blind_id": r["blind_id"], "studies": list(studies.values())})
    logs.append(
        {
            "pi_id": r["pi_id"],
            "blind_id": r["blind_id"],
            "registry_status": "complete",
            "publication_status": "complete",
            "unavailable_NCTs": sorted(set(leads) - set(previous)),
            "n_candidates": len(studies),
        }
    )
    for n, s in studies.items():
        p = s["protocolSection"]
        design = p.get("designModule", {})
        d = p["statusModule"].get("startDateStruct", {})
        w = window(r, d.get("date", ""))
        screen = linkage_screen(r, p, n in leads)
        if screen == "retrieved_surname_only_without_person_or_project_support" and n in archive_by_pi.get(
            r["pi_id"], set()
        ):
            screen = "historical_name_institution_or_grant_query_lead"
        screened.append(
            {
                "blind_id": r["blind_id"],
                "nct_id": n,
                "screen": screen,
                "window": w,
                "study_type": design.get("studyType"),
            }
        )
        if (
            design.get("studyType") != "INTERVENTIONAL"
            or (w == "after_5y" and (r["blind_id"], n) not in window_recovery)
            or screen == "retrieved_surname_only_without_person_or_project_support"
        ):
            continue
        card = {
            "case_id": r["blind_id"] + "_" + n,
            "blind_id": r["blind_id"],
            "awardee": r["name"],
            "first_name": r["first_name"],
            "last_name": r["last_name"],
            "K_institution": r["institution"],
            "K_start": r["start_date"],
            "end_5y": r["end_5y"],
            "K_title": r["title"],
            "K_abstract": r["abstract"],
            "K_source": r["source"],
            "K_core_project_num": r["core_project_num"],
            "window": w,
            "protocol": {k: v for k, v in p.items() if k not in ["contactsLocationsModule", "referencesModule"]},
            "leadership_entries": leadership(p),
            "documents": s.get("documentSection", s.get("documentsSection", {}))
            .get("largeDocumentModule", {})
            .get("largeDocs", []),
            "trial_source": "https://clinicaltrials.gov/study/" + n,
            "publication_lead": n in leads,
        }
        for field in ["K_title", "K_abstract"]:
            card[field] = re.sub(
                (
                    "(?i)\\b(?:(?:PA|PAR|PAS)-\\d{2}-\\d{3}|RFA-[A-Z]{2}-\\d{2}-\\d{3})\\b|(?:independ"
                    "ent\\s+)?clinical\\s+trials?\\s+(?:not\\s+allowed|required|optional)"
                ),
                "[funding designation redacted]",
                card[field],
            )
        card["publication_sources"] = leads.get(n, [])
        review.append(card)
dump(F / "linkage_screen_audit.json", screened)
dump(F / "trials_merged.json", merged)
dump(F / "search_audit.json", logs)
dump(F / "review_cases.json", review)
print(
    "FULL EVIDENCE MERGE",
    len(merged),
    "people",
    sum(len(r["studies"]) for r in merged),
    "all candidates;",
    len(review),
    "interventional candidate cases including pre-K; unavailable publication NCTs",
    len(unavailable),
)
print(
    "MERGE COVERAGE", len(merged), "/1527; remaining people explicitly pending publication retrieval or identity audit"
)
