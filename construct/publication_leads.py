"""Publication leads."""

import json
import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import UTC, datetime

from construct.reporter import OUT, RAW, dump, table

sample = json.loads((OUT / "sample_key_private.json").read_text())
logs = []
leads = []
for r in sample:
    query = f"{r['last_name']} {r['first_name']}[Full Author Name] AND clinicaltrials.gov[Secondary Source ID]"
    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?" + urllib.parse.urlencode(
        {"db": "pubmed", "term": query, "retmode": "json", "retmax": 1000}
    )
    path = RAW / f"pubmed_{r['pi_id']}_search.json"
    if path.exists():
        saved = json.loads(path.read_text())
        assert saved["query"] == query, "Source query or pagination mismatch; inspect the private capture locally."
        d = saved["response"]
    else:
        time.sleep(0.4)
        d = json.load(urllib.request.urlopen(url, timeout=60))
        dump(path, {"query": query, "url": url, "retrieved_at": datetime.now(UTC).isoformat(), "response": d})
    result = d["esearchresult"]
    ids = result["idlist"]
    assert len(ids) == int(result["count"]), "Source query or pagination mismatch; inspect the private capture locally."
    logs.append(
        {
            "blind_id": r["blind_id"],
            "pi_id": r["pi_id"],
            "query": query,
            "pmids": ";".join(ids),
            "n_articles": len(ids),
            "source": url,
            "status": "complete",
        }
    )
    if ids:
        xml = RAW / f"pubmed_{r['pi_id']}_articles.xml"
        if not xml.exists():
            url2 = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?" + urllib.parse.urlencode(
                {"db": "pubmed", "id": ",".join(ids), "retmode": "xml"}
            )
            time.sleep(0.4)
            xml.write_bytes(urllib.request.urlopen(url2, timeout=60).read())
        root = ET.fromstring(xml.read_bytes())
        assert len(root.findall("PubmedArticle")) == len(ids), (
            "Source query or pagination mismatch; inspect the private capture locally."
        )
        for a in root.findall("PubmedArticle"):
            pmid = a.findtext(".//PMID")
            title = "".join(a.find(".//ArticleTitle").itertext())
            ncts = sorted(set(re.findall("NCT\\d{8}", ET.tostring(a, encoding="unicode"))))
            for nct in ncts:
                leads.append(
                    {
                        "pi_id": r["pi_id"],
                        "blind_id": r["blind_id"],
                        "pmid": pmid,
                        "nct_id": nct,
                        "article_title": title,
                        "status": "publication_lead_not_PI_evidence",
                        "source": "https://pubmed.ncbi.nlm.nih.gov/" + pmid + "/",
                    }
                )
    print("PUBMED", len(ids), "papers", flush=True)
table(OUT / "sample_literature_search_log.csv", logs)
table(
    OUT / "sample_publication_leads.csv",
    leads,
    ["pi_id", "blind_id", "pmid", "nct_id", "article_title", "status", "source"],
)
print("PUBMED COMPLETE", len(logs), "people", len(leads), "publication-trial leads")
