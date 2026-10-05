"""Protocol pages."""

import hashlib
import json
import re
from pathlib import Path

from pypdf import PdfReader

from config import DATA_DIR
from construct.reporter import dump

F = DATA_DIR / "contemporaneous"
docs = []
rows = []
for s in json.loads((F / "protocol_sources.json").read_text()):
    if s["status"] not in ["text_available", "image_pdf_requires_visual_review"]:
        continue
    chunks = re.split("\\[PAGE (\\d+)\\]\\n", Path(s["local_text"]).read_text())
    pages = {int(chunks[i]): chunks[i + 1] for i in range(1, len(chunks), 2)}
    assert pages and set(pages) == set(range(1, len(pages) + 1)), (
        "Required source invariant failed; inspect the private input locally."
    )
    if "pages" in s:
        assert len(pages) == s["pages"], "Required source invariant failed; inspect the private input locally."
    sparse = [i for i, text in pages.items() if len(text.strip()) < 100]
    if sparse:
        docs.append(
            {
                "nct_id": s["nct_id"],
                "url": s["url"],
                "text_status": s["status"],
                "local_text": s["local_text"],
                "pages": len(pages),
                "sparse_pages": sparse,
            }
        )
dump(F / "protocol_sparse_pages_inventory.json", docs)
previous = (
    {r["url"]: r for r in json.loads((F / "protocol_mixed_page_audit.json").read_text())}
    if (F / "protocol_mixed_page_audit.json").exists()
    else {}
)


def large_image(resources, seen):
    if resources is None:
        return False
    resources = resources.get_object()
    objects = resources.get("/XObject")
    if objects is None:
        return False
    for value in objects.get_object().values():
        ref = (getattr(value, "idnum", None), getattr(value, "generation", None))
        if ref != (None, None) and ref in seen:
            continue
        seen.add(ref)
        obj = value.get_object()
        if obj.get("/Subtype") == "/Image" and min(obj.get("/Width", 0), obj.get("/Height", 0)) >= 600:
            return True
        if obj.get("/Subtype") == "/Form" and large_image(obj.get("/Resources"), seen):
            return True
    return False


for n, d in enumerate(docs, 1):
    if d["text_status"] != "text_available":
        continue
    path = Path(d["local_text"]).with_suffix(".pdf")
    assert path.exists(), "Required source invariant failed; inspect the private input locally."
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if d["url"] in previous:
        old = previous[d["url"]]
        assert all((old[k] == v for k, v in d.items())) and old.get("pdf_sha256", digest) == digest, (
            "Required source invariant failed; inspect the private input locally."
        )
        rows.append(dict(old, pdf_sha256=digest))
        continue
    reader = PdfReader(path)
    assert len(reader.pages) == d["pages"], "Required source invariant failed; inspect the private input locally."
    flagged = []
    other = []
    for number in d["sparse_pages"]:
        page = reader.pages[number - 1]
        image = large_image(page.get("/Resources"), set())
        content = page.get_contents()
        operations = len(content.operations) if content is not None else 0
        detail = {"page": number, "large_image": image, "content_operation_count": operations}
        (flagged if image or operations > 150 else other).append(detail)
    rows.append(
        dict(
            d,
            pdf_file=str(path),
            pdf_sha256=digest,
            pages_requiring_OCR=flagged,
            low_text_pages_without_large_image_or_complex_content=other,
        )
    )
    if n % 50 == 0:
        dump(F / "protocol_mixed_page_audit.json", rows)
        print(
            "MIXED PAGE AUDIT",
            "/",
            len(docs),
            "documents with OCR pages",
            sum(bool(r["pages_requiring_OCR"]) for r in rows),
            "OCR pages",
            sum(len(r["pages_requiring_OCR"]) for r in rows),
            flush=True,
        )
dump(F / "protocol_mixed_page_audit.json", rows)
print(
    "MIXED PAGE AUDIT COMPLETE",
    len(rows),
    "text-available protocols checked;",
    sum(bool(r["pages_requiring_OCR"]) for r in rows),
    "documents;",
    sum(len(r["pages_requiring_OCR"]) for r in rows),
    "pages need OCR. Unflagged sparse pages are not proven text-complete.",
    flush=True,
)
