"""Pubmed."""

import hashlib
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import UTC, date, datetime

from config import DATA_DIR
from construct.registry import name_terms, norm
from construct.reporter import dump

F = DATA_DIR / "contemporaneous"
R = F / "sources"
cohort = json.loads((F / "cohort_key_private.json").read_text())
progress = []
archives = [R / "pubmed_exact", R / "pubmed_prefix"]
known = {
    a["pmid"]: a
    for folder in archives
    for path in sorted(folder.glob("pubmed_person_*.json"))
    for a in json.loads(path.read_text())["articles"]
}
last_request = 0.0


def fetch(url):
    global last_request
    time.sleep(max(0, 1.1 - (time.monotonic() - last_request)))
    last_request = time.monotonic()
    return urllib.request.urlopen(url, timeout=90).read()


def parse(xml):
    root = ET.fromstring(xml.read_bytes())
    assert len(root) and all(x.tag in ["PubmedArticle", "PubmedBookArticle"] for x in root), (
        "Required source invariant failed; inspect the private input locally."
    )
    articles = []
    for a in root:
        if a.tag == "PubmedBookArticle":
            articles.append(
                {
                    "pmid": a.findtext(".//PMID"),
                    "record_type": "PubmedBookArticle",
                    "status": "retained_book_record_requires_separate_review",
                    "ncts": sorted(set(re.findall("NCT\\d{8}", ET.tostring(a, encoding="unicode")))),
                }
            )
            continue
        authors = [
            {
                "last": v.findtext("LastName", ""),
                "first": v.findtext("ForeName", ""),
                "affiliations": ["".join(x.itertext()) for x in v.findall("AffiliationInfo/Affiliation")],
                "identifiers": [{"source": x.get("Source"), "value": x.text} for x in v.findall("Identifier")],
            }
            for v in a.findall(".//Article/AuthorList/Author")
        ]
        articles.append(
            {
                "pmid": a.findtext(".//PMID"),
                "title": "".join(a.find(".//ArticleTitle").itertext()),
                "authors": authors,
                "publication_dates": [
                    {k: el.findtext(k, "") for k in ["Year", "Month", "Day", "MedlineDate"]}
                    for el in a.findall(".//JournalIssue/PubDate") + a.findall(".//Article/ArticleDate")
                ],
                "grants": [dict((el.tag, el.text) for el in g) for g in a.findall(".//Grant")],
                "ncts": sorted(set(re.findall("NCT\\d{8}", ET.tostring(a, encoding="unicode")))),
            }
        )
    assert len({a["pmid"] for a in articles}) == len(articles), (
        "Required source invariant failed; inspect the private input locally."
    )
    return articles


def person(r):
    variants = [
        f'''"{r["last_name"]} {given}{suffix}"[Full Author Name]''' for given in name_terms(r) for suffix in ["", " *"]
    ]
    inst = [
        x
        for x in norm(r["institution"]).split()
        if x
        not in {
            "university",
            "of",
            "the",
            "at",
            "and",
            "college",
            "medical",
            "medicine",
            "school",
            "hospital",
            "research",
            "center",
            "institute",
            "inc",
            "for",
            "health",
            "system",
            "state",
        }
        and len(x) > 3
    ]
    assert inst, "Required source invariant failed; inspect the private input locally."
    variants.append(f'''("{r["last_name"]} {r["first_name"][0]}*"[Author] AND "{max(inst, key=len)}"[Affiliation])''')
    author = " OR ".join(variants)
    start = date.fromisoformat(r["start_date"])
    prior = start.replace(year=start.year - 5).isoformat()
    q = (
        f'({author}) AND (("{prior}"[Date - Publication] : '
        f'"{r["start_date"]}"[Date - Publication]) OR clinicaltrials.gov[Secondary Source ID])'
    )
    output = R / f"pubmed_person_{r['pi_id']}.json"
    if output.exists():
        saved = json.loads(output.read_text())
        assert saved["query"] == q, "Required source invariant failed; inspect the private input locally."
        return {
            "pi_id": r["pi_id"],
            "blind_id": r["blind_id"],
            "n_articles": len(saved["articles"]),
            "status": "complete",
        }
    path = R / f"pubmed_{r['pi_id']}_search.json"
    if path.exists():
        saved = json.loads(path.read_text())
        assert saved["query"] == q, "Required source invariant failed; inspect the private input locally."
        d = saved["response"]
    else:
        url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?" + urllib.parse.urlencode(
            {"db": "pubmed", "term": q, "retmode": "json", "retmax": 10000}
        )
        d = json.loads(fetch(url))
        dump(path, {"query": q, "url": url, "retrieved_at": datetime.now(UTC).isoformat(), "response": d})
    ids = d["esearchresult"]["idlist"]
    assert len(ids) == int(d["esearchresult"]["count"]), (
        "Required source invariant failed; inspect the private input locally."
    )
    records = {x: known[x] for x in ids if x in known}
    for xml in sorted(R.glob(f"pubmed_{r['pi_id']}_extra_*.xml")):
        records.update({a["pmid"]: a for a in parse(xml)})
    missing = [x for x in ids if x not in records]
    for i in range(0, len(missing), 200):
        batch = missing[i : i + 200]
        token = hashlib.sha256(",".join(batch).encode()).hexdigest()[:12]
        xml = R / f"pubmed_{r['pi_id']}_extra_{token}.xml"
        url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?" + urllib.parse.urlencode(
            {"db": "pubmed", "id": ",".join(batch), "retmode": "xml"}
        )
        assert not xml.exists(), "Required source invariant failed; inspect the private input locally."
        xml.write_bytes(fetch(url))
        dump(xml.with_suffix(".request.json"), {"url": url, "retrieved_at": datetime.now(UTC).isoformat()})
        articles = parse(xml)
        assert {a["pmid"] for a in articles} == set(batch), (
            "Required source invariant failed; inspect the private input locally."
        )
        records.update({a["pmid"]: a for a in articles})
    articles = [records[x] for x in ids]
    assert len(articles) == len(set(ids)), "Required source invariant failed; inspect the private input locally."
    dump(
        output,
        {
            "pi_id": r["pi_id"],
            "blind_id": r["blind_id"],
            "query": q,
            "status": "complete",
            "reused_source_archives": [str(x) for x in archives],
            "articles": articles,
        },
    )
    return {"pi_id": r["pi_id"], "blind_id": r["blind_id"], "n_articles": len(articles), "status": "complete"}


progress = [person(r) for r in cohort]
dump(F / "publication_search_progress.json", sorted(progress, key=lambda x: x["blind_id"]))
print("PubMed people:", len(progress), "articles:", sum(r["n_articles"] for r in progress))
