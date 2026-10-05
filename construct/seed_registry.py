"""Seed registry."""

import json
import time
import urllib.parse
import urllib.request
from datetime import UTC, datetime

from construct.registry import matches
from construct.reporter import OUT, RAW, dump

cohort = json.loads((OUT / "cohort.json").read_text())
results = []
for i in range(0, len(cohort), 10):
    batch = cohort[i : i + 10]
    terms = []
    for r in batch:
        first = r["first_name"].replace('"', "")
        last = r["last_name"].replace('"', "")
        terms.extend([f'("{first}" AND "{last}")', f'''"{r["project_num"]}"''', f'''"{r["core_project_num"]}"'''])
    query = " OR ".join(terms)
    studies = []
    token = None
    page = 0
    while True:
        params = {"query.term": query, "pageSize": 100, "countTotal": "true", "format": "json"}
        if token:
            params["pageToken"] = token
        path = RAW / f"ct_seed_{i}_{page}.json"
        if path.exists():
            saved = json.loads(path.read_text())
            assert saved["query"] == query, "Source query or pagination mismatch; inspect the private capture locally."
            d = saved["response"]
        else:
            url = "https://clinicaltrials.gov/api/v2/studies?" + urllib.parse.urlencode(params)
            time.sleep(1.2)
            d = json.load(urllib.request.urlopen(url, timeout=90))
            dump(
                path,
                {"retrieved_at": datetime.now(UTC).isoformat(), "url": url, "query": query, "response": d},
            )
        if page == 0:
            total = d["totalCount"]
        studies.extend(d.get("studies", []))
        token = d.get("nextPageToken")
        page += 1
        if not token:
            break
    assert len(studies) == total, "Source query or pagination mismatch; inspect the private capture locally."
    assert len({s["protocolSection"]["identificationModule"]["nctId"] for s in studies}) == len(studies), (
        "Source query or pagination mismatch; inspect the private capture locally."
    )
    for r in batch:
        results.append(
            {"pi_id": r["pi_id"], "query": query, "studies": [s for s in studies if matches(r, s["protocolSection"])]}
        )
    print("CT", len(results), "/", len(cohort), "candidates", sum(len(x["studies"]) for x in results), flush=True)
dump(OUT / "trials_raw.json", results)
print(
    "CT COMPLETE",
    len(results),
    "PI searches;",
    sum(len(x["studies"]) for x in results),
    "candidate pairs",
    flush=True,
)
