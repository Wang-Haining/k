"""Protocols."""

import json
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from config import DATA_DIR
from construct.reporter import RAW, dump

F = DATA_DIR / "contemporaneous"
R = F / "sources"
key = {r["pi_id"]: r for r in json.loads((F / "cohort_key_private.json").read_text())}
sources = {
    s["nct_id"] + "_" + s["url"].rsplit("/", 1)[-1]: s for s in json.loads((F / "protocol_sources.json").read_text())
}
failures = []
items = json.loads((F / "trials_merged.json").read_text())
review = {
    (r["blind_id"], r["protocol"]["identificationModule"]["nctId"])
    for r in json.loads((F / "review_cases.json").read_text())
}
assert items and review, "Expected nonempty merged registry records and review cases"
for item in items:
    r = key[item["pi_id"]]
    for s in item["studies"]:
        p = s["protocolSection"]
        nct = p["identificationModule"]["nctId"]
        if (r["blind_id"], nct) not in review:
            continue
        for d in (
            s.get("documentSection", s.get("documentsSection", {})).get("largeDocumentModule", {}).get("largeDocs", [])
        ):
            if not d.get("hasProtocol"):
                continue
            filename = nct + "_" + d["filename"]
            pdf = R / filename
            txt = pdf.with_suffix(".txt")
            meta = R / (filename + ".source.json")
            url = f"https://cdn.clinicaltrials.gov/large-docs/{nct[-2:]}/{nct}/{d['filename']}"
            if (RAW / filename).exists() and (RAW / filename).with_suffix(".txt").exists():
                source = {
                    "nct_id": nct,
                    "document_date": d.get("date"),
                    "url": url,
                    "local_text": str((RAW / filename).with_suffix(".txt")),
                    "status": "text_available",
                    "retrieved_at": "see_original_protocol_sources.csv",
                }
            elif meta.exists():
                source = json.loads(meta.read_text())
                if source["status"] == "text_available":
                    assert Path(source["local_text"]).exists(), (
                        "Required source invariant failed; inspect the private input locally."
                    )
            else:
                try:
                    if not pdf.exists():
                        time.sleep(1.2)
                        pdf.write_bytes(urllib.request.urlopen(url, timeout=60).read())
                    reader = PdfReader(pdf)
                    pages = [page.extract_text() for page in reader.pages]
                    text = "\n".join((f"\n[PAGE {i + 1}]\n{p}" for i, p in enumerate(pages)))
                    txt.write_text(text)
                    source = {
                        "nct_id": nct,
                        "document_date": d.get("date"),
                        "url": url,
                        "local_text": str(txt),
                        "pages": len(pages),
                        "status": "text_available"
                        if any(p.strip() for p in pages)
                        else "image_pdf_requires_visual_review",
                        "retrieved_at": datetime.now(UTC).isoformat(),
                    }
                except (urllib.error.HTTPError, PdfReadError) as e:
                    source = {
                        "nct_id": nct,
                        "document_date": d.get("date"),
                        "url": url,
                        "status": "source_error",
                        "error": str(e),
                        "retrieved_at": datetime.now(UTC).isoformat(),
                    }
                dump(meta, source)
            sources[filename] = source
    print("PROTOCOL PROGRESS", "sources", len(sources), flush=True)
    dump(F / "protocol_sources.json", list(sources.values()))
failures = [s for s in sources.values() if s["status"] == "source_error"]
print(
    "PROTOCOL HARVEST",
    len(items),
    "completed search records",
    len(sources),
    "sources",
    "errors",
    len(failures),
    flush=True,
)
if failures:
    raise SystemExit(
        "Protocol source errors retained explicitly in protocol_sources.json; no aff"
        "ected role timing may be counted as confirmed"
    )
