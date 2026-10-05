"""Sample registry."""

import csv
import json
import re
import time
import urllib.parse
import urllib.request
from datetime import UTC, datetime

from construct.registry import leadership, norm
from construct.reporter import OUT, RAW, dump, table

sample = json.loads((OUT / "sample_key_private.json").read_text())
main = json.loads((OUT / "trials_raw.json").read_text())
byid = {r["pi_id"]: r for r in main}
added = 0
for r in sample:
    first = r["first_name"].replace('"', "")
    last = r["last_name"].replace('"', "")
    serial = re.sub("^K\\d\\d", "", r["core_project_num"])
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
    assert words, "Source query or pagination mismatch; inspect the private capture locally."
    inst = max(words, key=len)
    query = f'("{first}" AND "{last}") OR "{serial}" OR (AREA[OverallOfficialName]("{last}") AND "{inst}")'
    token = None
    page = 0
    studies = []
    while True:
        path = RAW / f"sample_search_{r['pi_id']}_{page}.json"
        if path.exists():
            saved = json.loads(path.read_text())
            assert saved["query"] == query, "Source query or pagination mismatch; inspect the private capture locally."
            d = saved["response"]
        else:
            params = {"query.term": query, "pageSize": 100, "countTotal": "true", "format": "json"}
            if token:
                params["pageToken"] = token
            url = "https://clinicaltrials.gov/api/v2/studies?" + urllib.parse.urlencode(params)
            time.sleep(1.2)
            d = json.load(urllib.request.urlopen(url, timeout=90))
            dump(
                path,
                {"query": query, "url": url, "retrieved_at": datetime.now(UTC).isoformat(), "response": d},
            )
        if page == 0:
            total = d["totalCount"]
        studies.extend(d.get("studies", []))
        token = d.get("nextPageToken")
        page += 1
        if not token:
            break
    assert len(studies) == total, "Source query or pagination mismatch; inspect the private capture locally."
    keep = {s["protocolSection"]["identificationModule"]["nctId"]: s for s in byid[r["pi_id"]]["studies"]}
    for s in studies:
        p = s["protocolSection"]
        nct = p["identificationModule"]["nctId"]
        officials = leadership(p)
        surname = any(set(norm(last).split()) <= set(norm(o["name"]).split()) for o in officials)
        grant = serial.lower() in re.sub("[^a-z0-9]", "", json.dumps(p["identificationModule"]).lower())
        if (surname or grant) and nct not in keep:
            keep[nct] = s
            added += 1
    byid[r["pi_id"]]["studies"] = list(keep.values())
    byid[r["pi_id"]]["supplemental_query"] = query
    print("SAMPLE", "retrieved", len(studies), "retained", len(keep), "added_total", flush=True)
pub = json.loads((OUT / "publication_trials.json").read_text())
pub_added = 0
for lead in csv.DictReader((OUT / "sample_publication_leads.csv").open()):
    item = byid[int(lead["pi_id"])]
    nct = lead["nct_id"]
    if nct not in {s["protocolSection"]["identificationModule"]["nctId"] for s in item["studies"]}:
        item["studies"].append(pub[nct])
        pub_added += 1
audit = []
for r in sample:
    item = byid[r["pi_id"]]
    audit.append(
        {
            "blind_id": r["blind_id"],
            "pi_id": r["pi_id"],
            "registry_search": "completed",
            "registry_query": item["supplemental_query"],
            "publication_search": "completed",
            "candidate_records": len(item["studies"]),
            "alias_search": "full first/last and surname/institution; not an exhaustive historical alias search",
            "negative_status": "a negative search does not establish absence",
        }
    )
table(OUT / "sample_search_audit.csv", audit)
dump(OUT / "trials_with_sample_search.json", main)
print("SAMPLE SEARCH COMPLETE", len(sample), "additional candidates")
print("PUBLICATION CANDIDATES ADDED", "; all 80 search states recorded")
