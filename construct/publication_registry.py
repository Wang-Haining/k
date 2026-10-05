"""Publication registry."""

import csv
import json
import time
import urllib.parse
import urllib.request
from datetime import UTC, datetime

from construct.reporter import OUT, RAW, dump

leads = list(csv.DictReader((OUT / "sample_publication_leads.csv").open()))
ncts = sorted({r["nct_id"] for r in leads})
studies = {}
for i in range(0, len(ncts), 50):
    batch = ncts[i : i + 50]
    path = RAW / f"publication_trials_{i}.json"
    query = " OR ".join(batch)
    if path.exists():
        saved = json.loads(path.read_text())
        assert saved["query"] == query, "Source query or pagination mismatch; inspect the private capture locally."
        d = saved["response"]
    else:
        url = "https://clinicaltrials.gov/api/v2/studies?" + urllib.parse.urlencode(
            {"query.id": query, "pageSize": 100, "countTotal": "true"}
        )
        time.sleep(1.2)
        d = json.load(urllib.request.urlopen(url, timeout=90))
        dump(path, {"query": query, "url": url, "retrieved_at": datetime.now(UTC).isoformat(), "response": d})
    assert not d.get("nextPageToken"), "Source query or pagination mismatch; inspect the private capture locally."
    assert d["totalCount"] == len(batch), "Source query or pagination mismatch; inspect the private capture locally."
    for s in d["studies"]:
        studies[s["protocolSection"]["identificationModule"]["nctId"]] = s
    print("PUBLICATION NCTS", len(studies), "/", len(ncts), flush=True)
assert set(studies) == set(ncts), "Source query or pagination mismatch; inspect the private capture locally."
dump(OUT / "publication_trials.json", studies)
print("PUBLICATION RETRIEVAL COMPLETE", len(leads), "leads", len(studies), "trials; authorship is not PI evidence")
