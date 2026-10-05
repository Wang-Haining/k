"""Start dates."""

import hashlib
import json
from datetime import datetime
from pathlib import Path

from config import DATA_DIR
from construct.linkage import followup_window
from construct.reporter import dump

F = DATA_DIR / "contemporaneous"
cases = json.loads((F / "review_cases.json").read_text())
manifest = json.loads((F / "historical_registry_addenda.json").read_text())
historical = {}
source_hashes = {}
for a in manifest:
    if a["snapshot_date"] != "2022-11-09":
        continue
    path = Path(a["local_text"])
    text = path.read_text()
    assert hashlib.sha256(text.encode()).hexdigest() == a["text_sha256"], (
        "Required source invariant failed; inspect the private input locally."
    )
    for r in json.loads(text)["verbatim_table_rows"].get("studies", []):
        if r["start_date_type"].upper() != "ACTUAL" or not r["start_month_year"]:
            continue
        original = r["start_month_year"]
        fmt = "%B %d, %Y" if "," in original else "%B %Y" if " " in original else "%Y"
        date = datetime.strptime(original, fmt).strftime(
            "%Y-%m-%d" if "," in original else "%Y-%m" if " " in original else "%Y"
        )
        historical.setdefault(a["nct_id"], []).append(
            {
                "historical_nct_id": r["nct_id"],
                "start": date,
                "original_date": original,
                "snapshot_date": a["snapshot_date"],
                "source": a["local_text"],
                "source_sha256": a["text_sha256"],
            }
        )
conflicts = []
withdrawn = []
for c in cases:
    s = c["protocol"]["statusModule"]
    n = c["protocol"]["identificationModule"]["nctId"]
    start = s.get("startDateStruct", {})
    e = c["protocol"].get("designModule", {}).get("enrollmentInfo", {})
    if (
        s.get("overallStatus") == "WITHDRAWN"
        and start.get("type") == "ACTUAL"
        and (e.get("type") == "ACTUAL")
        and (e.get("count") == 0)
    ):
        withdrawn.append(
            {
                "case_id": c["case_id"],
                "trial_source": c["trial_source"],
                "status": "WITHDRAWN",
                "start": start,
                "enrollment": e,
                "why_stopped": s.get("whyStopped"),
            }
        )
    if start.get("type") != "ACTUAL":
        continue
    now = followup_window(c["K_start"], c["end_5y"], start.get("date"))
    for old in historical.get(n, []):
        before = followup_window(c["K_start"], c["end_5y"], old["start"])
        if before in ["pre_K", "inside", "after_5y"] and now in ["pre_K", "inside", "after_5y"] and (before != now):
            conflicts.append(
                {
                    "case_id": c["case_id"],
                    "current_start": start,
                    "current_window": now,
                    "historical_start": old,
                    "historical_window": before,
                    "K_start": c["K_start"],
                    "end_5y": c["end_5y"],
                }
            )
result = {
    "candidate_pairs": len(cases),
    "withdrawn_zero_with_actual_start": withdrawn,
    "historical_current_actual_start_window_conflicts": conflicts,
    "unresolved_case_ids": sorted({r["case_id"] for r in withdrawn + conflicts}),
    "rule": (
        "Conflicting metadata do not establish an initiated trial in a date window. "
        "Otherwise eligible cases remain unknown; role evidence and relationship jud"
        "gments stay separate. Historical aliases do not prove identical protocol co"
        "ntent."
    ),
    "input_sha256": {
        name: hashlib.sha256((F / name).read_bytes()).hexdigest()
        for name in ["review_cases.json", "historical_registry_addenda.json"]
    },
}
dump(F / "source_start_conflicts.json", result)
print(
    "START AUDIT",
    len(cases),
    "pairs;",
    len(withdrawn),
    "withdrawn/zero with actual start;",
    len(conflicts),
    "historical/current window conflicts;",
    len(result["unresolved_case_ids"]),
    "unique cases retained as timing uncertainty",
)
