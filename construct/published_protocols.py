"""Published protocols."""

import hashlib
import json
import re
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import UTC, datetime

from config import DATA_DIR
from construct.reporter import dump

F = DATA_DIR / "contemporaneous"
R = F / "sources"
inventory = json.loads((F / "protocol_publication_inventory.json").read_text())
assert len(inventory) == 535, "Required source invariant failed; inspect the private input locally."
mask = (
    "(?i)\\b(?:(?:PA|PAR|PAS)-\\d{2}-\\d{3}|RFA-[A-Z]{2}-\\d{2}-\\d{3})\\b|(?:independ"
    "ent\\s+)?clinical\\s+trials?\\s+(?:not\\s+allowed|required|optional)"
)
records = []
addenda = []
for r in inventory:
    record = {"pmid": r["pmid"], "pmcid": r["pmcid"], "title": r["title"]}
    if not r["pmcid"]:
        record.update(status="no_PMC_identifier; publisher_full_text_not_retrieved")
    else:
        url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pmc&id=" + r["pmcid"][3:]
        xml = R / ("published_protocol_" + r["pmcid"] + ".xml")
        meta = xml.with_suffix(".source.json")
        if meta.exists() and xml.exists():
            url = json.loads(meta.read_text())["source_url"]
        record["source_url"] = url
        if meta.exists() and (not xml.exists()):
            record.update(json.loads(meta.read_text()))
        else:
            if not xml.exists():
                try:
                    time.sleep(1.2)
                    xml.write_bytes(urllib.request.urlopen(url, timeout=60).read())
                except urllib.error.HTTPError as e:
                    record.update(
                        status="source_unavailable" if e.code in [403, 404] else "source_http_error",
                        error=str(e),
                        retrieved_at=datetime.now(UTC).isoformat(),
                    )
                    dump(meta, record)
            if xml.exists():
                root = ET.fromstring(xml.read_bytes())
                assert root.tag in ["article", "article-set", "pmc-articleset"], (
                    "Required source invariant failed; inspect the private input locally."
                )
                if root.find(".//body") is None:
                    assert root.find(".//article-meta") is not None, (
                        "Required source invariant failed; inspect the private input locally."
                    )
                    record.update(
                        status="metadata_only; full_text_not_supplied_by_PMC_API",
                        xml_file=str(xml),
                        retrieved_at=datetime.now(UTC).isoformat(),
                    )
                    dump(meta, record)
                    records.append(record)
                    dump(F / "protocol_publication_retrieval.json", records)
                    dump(F / "protocol_publication_addenda.json", addenda)
                    print(
                        "PUBLISHED PROTOCOLS",
                        len(records),
                        "/",
                        len(inventory),
                        "metadata only; no PI evidence inferred",
                        flush=True,
                    )
                    continue
                chunks = []

                def walk(el, chunks=chunks):
                    if el.tag == "ref-list":
                        return
                    block = el.tag in [
                        "p",
                        "title",
                        "contrib",
                        "aff",
                        "pub-date",
                        "article-id",
                        "fn",
                        "funding-group",
                        "notes",
                        "sec",
                    ]
                    if block:
                        chunks.append("\n")
                    if el.text:
                        chunks.append(el.text)
                    for child in el:
                        walk(child)
                        if child.tail:
                            chunks.append(child.tail)
                    if block:
                        chunks.append("\n")

                walk(root)
                body = "".join(chunks)
                dates = [
                    dict(d.attrib, year=d.findtext("year"), month=d.findtext("month"), day=d.findtext("day"))
                    for d in root.findall(".//article-meta/pub-date")
                ]
                header = (
                    "[SOURCE PUBLICATION DATE METADATA]\n"
                    + json.dumps(dates, ensure_ascii=False)
                    + "\n[PROTOCOL ARTICLE TEXT; bibliography excluded, raw XML preserved]\n"
                )
                text = re.sub(mask, "[funding designation redacted]", header + body)
                assert len(text) > 500, "Required source invariant failed; inspect the private input locally."
                target = F / "packets" / ("published_protocol_" + r["pmcid"] + ".txt")
                target.write_text(text)
                ncts = sorted(set(re.findall("NCT\\d{8}", body)))
                record.update(
                    status="available",
                    local_text=str(target),
                    xml_file=str(xml),
                    publication_dates=dates,
                    nct_ids_outside_bibliography=ncts,
                    retrieved_at=datetime.now(UTC).isoformat(),
                    xml_sha256=hashlib.sha256(xml.read_bytes()).hexdigest(),
                )
                dump(meta, record)
                for nct in ncts:
                    addenda.append(
                        {
                            "nct_id": nct,
                            "addendum_id": "PMID" + r["pmid"] + "_" + nct,
                            "evidence_kind": "published_protocol",
                            "source_url": url,
                            "pmid": r["pmid"],
                            "pmcid": r["pmcid"],
                            "publication_dates": dates,
                            "document_date_metadata": None,
                            "local_text": str(target),
                            "image_pages": [],
                            "method": (
                                "Public protocol article, bibliography excluded; verify target-trial associa"
                                "tion and explicit overall PI role, authorship alone is insufficient; public"
                                "ation dates are not trial-start dates."
                            ),
                            "text_sha256": hashlib.sha256(text.encode()).hexdigest(),
                        }
                    )
    records.append(record)
    dump(F / "protocol_publication_retrieval.json", records)
    dump(F / "protocol_publication_addenda.json", addenda)
    print(
        "PUBLISHED PROTOCOLS",
        len(records),
        "/",
        len(inventory),
        "available",
        sum(x["status"] == "available" for x in records),
        "NCT-source addenda",
        len(addenda),
        flush=True,
    )
assert len(records) == 535 and len({r["pmid"] for r in records}) == 535, (
    "Required source invariant failed; inspect the private input locally."
)
print(
    "PUBLISHED PROTOCOL RETRIEVAL COMPLETE",
    len(records),
    "records;",
    sum(x["status"] == "available" for x in records),
    "public full texts;",
    len(addenda),
    "NCT source supplements; unavailable records remain explicit",
    flush=True,
)
errors = [r for r in records if r["status"] == "source_http_error"]
if errors:
    raise SystemExit("Published protocol HTTP errors retained explicitly: " + ",".join(r["pmid"] for r in errors))
