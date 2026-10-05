"""Ktrial publications."""

import json
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

from config import DATA_DIR

RAW, OUT = (DATA_DIR / "sources/ktrial_pubmed", DATA_DIR / "derived" / "ktrial_pubmed.json")
EU = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
INPUT = DATA_DIR / "derived" / "ktrial_panel_input_private.json"


def get(url, cache):
    f = RAW / cache
    if f.exists():
        return f.read_text()
    txt = urllib.request.urlopen(url, timeout=60).read().decode()
    f.write_text(txt)
    time.sleep(0.4)
    return txt


def author(a):
    return {
        "last": a.findtext("LastName") or a.findtext("CollectiveName") or "",
        "fore": a.findtext("ForeName") or "",
        "initials": a.findtext("Initials") or "",
    }


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    ncts = sorted({r["nct"] for r in json.loads(INPUT.read_text())})
    pm = {}
    for n in ncts:
        q = urllib.parse.quote(f"{n}[si] OR {n}[tiab]")
        ids = json.loads(get(f"{EU}esearch.fcgi?db=pubmed&retmode=json&retmax=50&term={q}", f"es_{n}.json"))[
            "esearchresult"
        ]["idlist"]
        pm[n] = ids
    pmids = sorted({i for v in pm.values() for i in v})
    meta = {}
    for k in range(0, len(pmids), 150):
        chunk = pmids[k : k + 150]
        root = ET.fromstring(get(f"{EU}efetch.fcgi?db=pubmed&retmode=xml&id={','.join(chunk)}", f"ef_{k:05d}.xml"))
        for art in root.findall(".//PubmedArticle"):
            pid = art.findtext(".//PMID")
            au = [author(a) for a in art.findall(".//AuthorList/Author")]
            meta[pid] = {
                "year": art.findtext(".//PubDate/Year") or (art.findtext(".//PubDate/MedlineDate") or "")[:4],
                "types": [t.text for t in art.findall(".//PublicationType")],
                "first": au[0] if au else {},
                "last": au[-1] if au else {},
                "n_authors": len(au),
            }
    out = {n: [dict(meta[i], pmid=i) for i in ids if i in meta] for n, ids in pm.items()}
    OUT.write_text(json.dumps(out))
    print(len(ncts), "NCTs;", sum(bool(v) for v in out.values()), "with >=1 PubMed record;", len(pmids), "PMIDs")


if __name__ == "__main__":
    main()
