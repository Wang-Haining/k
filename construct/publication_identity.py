"""Publication identity."""

import calendar
import hashlib
import json
import re
from datetime import UTC, date, datetime

from config import DATA_DIR
from construct.publication_metadata import author_evidence, identity_status, load_metadata
from construct.reporter import dump

F = DATA_DIR / "contemporaneous"
R = F / "sources"
months = {name.lower(): i for i in range(1, 13) for name in [calendar.month_abbr[i], calendar.month_name[i]]}


def date_interval(record):
    if not record["Year"]:
        years = re.findall("\\b(?:19|20)\\d{2}\\b", record["MedlineDate"])
        return (min(years) + "-01-01", max(years) + "-12-31") if years else None
    y = int(record["Year"])
    m = record["Month"]
    d = record["Day"]
    if not m:
        return (f"{y}-01-01", f"{y}-12-31")
    m = int(m) if m.isdigit() else months.get(m.lower())
    if m is None:
        return (f"{y}-01-01", f"{y}-12-31")
    assert 1 <= m <= 12, "Required source invariant failed; inspect the private input locally."
    if not d:
        return (f"{y}-{m:02d}-01", f"{y}-{m:02d}-{calendar.monthrange(y, m)[1]:02d}")
    value = date(y, m, int(d)).isoformat()
    return (value, value)


def date_status(r, dates):
    intervals = [x for x in [date_interval(d) for d in dates] if x]
    if not intervals:
        return ("date_unresolved", None)
    lo = min(x[0] for x in intervals)
    hi = min(x[1] for x in intervals)
    start = date.fromisoformat(r["start_date"])
    prior = start.replace(year=start.year - 5).isoformat()
    if hi < prior or lo >= r["start_date"]:
        return ("outside_preK_window", [lo, hi])
    return ("in_preK_window" if prior <= lo and hi < r["start_date"] else "date_unresolved", [lo, hi])


def classify_person(r, articles, metadata, source_file):
    evidence = {a["pmid"]: author_evidence(r, a, metadata[a["pmid"]]) for a in articles}
    anchor_evidence = [dict(p, pmid=pmid) for pmid, people in evidence.items() for p in people if p["anchor_reasons"]]
    anchors = {v for p in anchor_evidence for v in p["ORCIDs"]}
    audit = []
    for a in articles:
        pmid = a["pmid"]
        meta = metadata[pmid]
        people = evidence[pmid]
        status, reason = identity_status(meta, people, anchors)
        when, interval = date_status(r, meta["publication_dates"])
        assert set(a["ncts"]) == {p["nct_id"] for p in meta["nct_provenance"]}, (
            "Required source invariant failed; inspect the private input locally."
        )
        audit.append(
            {
                "pi_id": r["pi_id"],
                "blind_id": r["blind_id"],
                "pmid": pmid,
                "status": status,
                "identity_reason": reason,
                "source_file": source_file,
                "xml_source_file": meta["xml_source_file"],
                "author_list_complete": meta["author_list_complete"],
                "collective_names": meta["collective_names"],
                "author_evidence": people,
                "anchor_evidence": [
                    p
                    for p in anchor_evidence
                    if p["pmid"] == pmid or set(p["ORCIDs"]) & {v for person in people for v in person["ORCIDs"]}
                ],
                "ncts": a["ncts"],
                "nct_provenance": meta["nct_provenance"],
                "publication_dates": meta["publication_dates"],
                "date_status": when,
                "date_interval": interval,
                "record_type": a.get("record_type", "PubmedArticle"),
            }
        )
    return audit


def main():
    key = json.loads((F / "cohort_key_private.json").read_text())
    snapshots = []
    wanted = set()
    people = []
    for r in key:
        path = R / f"pubmed_person_{r['pi_id']}.json"
        if not path.exists():
            continue
        before = path.stat()
        content = path.read_bytes()
        after = path.stat()
        assert (before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns) and len(
            content
        ) == after.st_size, "Required source invariant failed; inspect the private input locally."
        saved = json.loads(content)
        assert saved["status"] == "complete" and saved["pi_id"] == r["pi_id"], (
            "Required source invariant failed; inspect the private input locally."
        )
        articles = saved["articles"]
        assert len({a["pmid"] for a in articles}) == len(articles), (
            "Required source invariant failed; inspect the private input locally."
        )
        people.append(
            {
                "blind_id": r["blind_id"],
                "pi_id": r["pi_id"],
                "source_file": str(path),
                "sha256": hashlib.sha256(content).hexdigest(),
                "n_articles": len(articles),
            }
        )
        snapshots.append((r, articles, str(path)))
        wanted.update(a["pmid"] for a in articles)
    assert snapshots, "Required source invariant failed; inspect the private input locally."
    metadata = load_metadata(R, wanted, {r["pi_id"] for r, _, _ in snapshots})
    audit = []
    for r, articles, path in snapshots:
        records = classify_person(r, articles, metadata, path)
        audit.extend(records)
    for name, records in [
        ("publication_all_article_identity_audit.json", audit),
    ]:
        path = F / name
        temporary = path.with_suffix(".json.tmp")
        dump(temporary, records)
        temporary.replace(path)
    audit_path = F / "publication_all_article_identity_audit.json"
    snapshot = {
        "status": "complete_for_included_people",
        "created_at": datetime.now(UTC).isoformat(),
        "cohort_n": len(key),
        "audited_people_n": len(snapshots),
        "complete_cohort": len(snapshots) == len(key),
        "publication_audit_file": str(audit_path),
        "publication_audit_sha256": hashlib.sha256(audit_path.read_bytes()).hexdigest(),
        "people": people,
    }
    path = F / "publication_identity_snapshot.json"
    temporary = path.with_suffix(".json.tmp")
    dump(temporary, snapshot)
    temporary.replace(path)
    print(
        "publication identity:",
        len(snapshots),
        "people;",
        len(audit),
        "articles;",
        len(key) - len(snapshots),
        "missing captures",
    )


if __name__ == "__main__":
    main()
