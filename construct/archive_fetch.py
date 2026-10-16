"""Archive fetch."""

import hashlib
import json
import time
import urllib.parse
import urllib.request
from datetime import UTC, datetime

from config import DATA_DIR
from construct.reporter import dump

F = DATA_DIR / "contemporaneous"
R = F / "sources"
leads = json.loads((F / "archive_candidate_retrieval.json").read_text())["new_leads"]
assert leads, "Required source invariant failed; inspect the private input locally."
needed = {
    r["nct_id"]
    for r in leads
    if r["current_record_status"] == "local_copy_missing_coordinator_fetch_needed"
    and r["archive_screen"]["interventional"]
    and (r["archive_screen"]["window"] != "after_5y")
}
later = json.loads((F / "archive_2024_candidate_retrieval.json").read_text())
additional = (
    set(later["query_compatible_missing_current_trial_ids"])
    | {
        r["nct_id"]
        for r in leads
        if r["current_query_compatible"] and r["current_record_status"] == "local_copy_missing_coordinator_fetch_needed"
    }
) - needed
priority = json.loads((F / "archive_fetch_order.json").read_text())
assert set(priority) <= needed, "Required source invariant failed; inspect the private input locally."
ids = priority + sorted(needed - set(priority)) + sorted(additional)
records = {}
resolved = {}
absent = []
sources = []
aliases = []
for offset in range(0, len(ids), 50):
    batch = ids[offset : offset + 50]
    query = " OR ".join(batch)
    path = R / ("archive_current_" + hashlib.sha256(query.encode()).hexdigest()[:12] + ".json")
    if path.exists():
        saved = json.loads(path.read_text())
        assert saved["query"] == query, "Required source invariant failed; inspect the private input locally."
    else:
        url = "https://clinicaltrials.gov/api/v2/studies?" + urllib.parse.urlencode(
            {"query.id": query, "pageSize": 100, "countTotal": "true"}
        )
        time.sleep(1.2)
        response = json.load(urllib.request.urlopen(url, timeout=90))
        saved = {
            "url": url,
            "query": query,
            "retrieved_at": datetime.now(UTC).isoformat(),
            "response": response,
        }
        dump(path, saved)
    response = saved["response"]
    assert not response.get("nextPageToken") and len(response["studies"]) == response["totalCount"], (
        "Required source invariant failed; inspect the private input locally."
    )
    got = {s["protocolSection"]["identificationModule"]["nctId"]: s for s in response["studies"]}
    assert len(got) == len(response["studies"]), "Required source invariant failed; inspect the private input locally."
    for n, s in got.items():
        identity = s["protocolSection"]["identificationModule"]
        requested = ({n} | set(identity.get("nctIdAliases", []))) & set(batch)
        assert requested, "Required source invariant failed; inspect the private input locally."
        for old in requested:
            assert old not in resolved or resolved[old] == n, (
                "Required source invariant failed; inspect the private input locally."
            )
            resolved[old] = n
            if old != n:
                aliases.append(
                    {
                        "requested_nct_id": old,
                        "canonical_nct_id": n,
                        "source": str(path),
                        "exact_registry_aliases": identity["nctIdAliases"],
                    }
                )
    records.update(got)
    absent.extend(n for n in batch if n not in resolved)
    sources.append(str(path))
    dump(
        F / "archive_current_fetch_progress.json",
        {
            "requested": len(ids),
            "queries_complete": len(sources),
            "IDs_queried": min(offset + 50, len(ids)),
            "returned": len(records),
            "resolved_requested_IDs": len(resolved),
            "not_returned": absent,
            "explicit_registry_aliases": aliases,
            "sources": sources,
            "complete": offset + 50 >= len(ids),
            "interpretation": (
                "Current record retrieval for archived leads, not identity or outcome adjudi"
                "cation. Explicit registry aliases are canonicalized, never counted as two t"
                "rials."
            ),
        },
    )
    print("ARCHIVE CURRENT FETCH", "/", len(ids), "returned", len(records), "not returned", len(absent), flush=True)
assert len(resolved) + len(absent) == len(ids), "Required source invariant failed; inspect the private input locally."
