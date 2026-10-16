"""Protocol encoded ocr."""

import hashlib
import json
import os
import re
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from config import DATA_DIR
from construct.reporter import dump

F = DATA_DIR / "contemporaneous"
R = F / "sources" / "font_ocr"
R.mkdir(exist_ok=True)
sources = json.loads((F / "protocol_sources.json").read_text())
docs = []
terms = ["3ULQFLSDO", "3URWRFRO", ",QYHVWLJDWRU", "9HUVLRQ", "$PHQGPHQW", "&OLQLFDO"]
for s in sources:
    if s["status"] not in ["text_available", "image_pdf_requires_visual_review"]:
        continue
    chunks = re.split("\\[PAGE (\\d+)\\]\\n", Path(s["local_text"]).read_text())
    pages = []
    assert len(chunks) > 1, "Required source invariant failed; inspect the private input locally."
    for j in range(1, len(chunks), 2):
        t = chunks[j + 1]
        matched = [x for x in terms if x in t]
        bad = sum(ord(c) < 32 and c not in "\n\t\r" for c in t)
        cid = len(re.findall("\\(cid:\\d+\\)", t))
        repl = t.count("�")
        if matched or bad >= 20 or cid >= 10 or (repl >= 10):
            pages.append(
                {
                    "page": int(chunks[j]),
                    "encoded_signatures": matched,
                    "control_characters": bad,
                    "cid_tokens": cid,
                    "replacement_characters": repl,
                }
            )
    if pages:
        docs.append(
            {
                "nct_id": s["nct_id"],
                "url": s["url"],
                "document_date": s["document_date"],
                "local_text": s["local_text"],
                "pdf_file": str(Path(s["local_text"]).with_suffix(".pdf")),
                "pages": (len(chunks) - 1) // 2,
                "pages_requiring_OCR": pages,
            }
        )
assert docs, "Required source invariant failed; inspect the private input locally."
dump(F / "protocol_encoded_page_audit.json", docs)
print(
    "FONT AUDIT",
    len(sources),
    "sources;",
    len(docs),
    "documents;",
    sum(len(d["pages_requiring_OCR"]) for d in docs),
    "pages",
    flush=True,
)
mask = (
    "(?i)\\b(?:(?:PA|PAR|PAS)-\\d{2}-\\d{3}|RFA-[A-Z]{2}-\\d{2}-\\d{3})\\b|(?:independ"
    "ent\\s+)?clinical\\s+trials?\\s+(?:not\\s+allowed|required|optional)"
)
env = dict(os.environ, OMP_THREAD_LIMIT="1")
started = time.monotonic()


def extract(d):
    pdf = Path(d["pdf_file"])
    stem = pdf.stem
    folder = R / stem
    folder.mkdir(exist_ok=True)
    meta = folder / "source.json"
    pages = [p["page"] for p in d["pages_requiring_OCR"]]
    digest = hashlib.sha256(pdf.read_bytes()).hexdigest()
    if meta.exists():
        row = json.loads(meta.read_text())
        assert row["pdf_sha256"] == digest and row["page_numbers"] == pages and Path(row["local_text"]).exists(), (
            "Required source invariant failed; inspect the private input locally."
        )
        return row
    texts = []
    images = []
    reused = 0
    for n in pages:
        target = folder / f"page-{n:04d}"
        prior = F / "sources" / "mixed_ocr" / stem / f"page-{n:04d}"
        if prior.with_suffix(".txt").exists():
            target = prior
            reused += 1
        png = target.with_suffix(".png")
        txt = target.with_suffix(".txt")
        if not png.exists():
            subprocess.run(
                [
                    "pdftoppm",
                    "-f",
                    str(n),
                    "-l",
                    str(n),
                    "-singlefile",
                    "-r",
                    "200",
                    "-gray",
                    "-png",
                    str(pdf),
                    str(target),
                ],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
            )
        if not txt.exists():
            subprocess.run(
                ["tesseract", str(png), str(target), "-l", "eng"],
                env=env,
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
            )
        texts.append(f"[PAGE {n}]\n" + txt.read_text())
        images.append(str(png))
    text = re.sub(mask, "[funding designation redacted]", "\n".join(texts))
    target = F / "packets" / f"protocol_{stem}.font.ocr.txt"
    target.write_text(text)
    row = {
        "nct_id": d["nct_id"],
        "source_url": d["url"],
        "document_date_metadata": d["document_date"],
        "local_text": str(target),
        "image_pages": images,
        "page_numbers": pages,
        "method": (
            "tesseract_eng_200dpi; font-encoded or replacement/control-character pages; "
            "verify decisive PI/date text visually"
        ),
        "pdf_sha256": digest,
        "text_sha256": hashlib.sha256(text.encode()).hexdigest(),
        "addendum_id": stem + "_FONT_OCR",
        "reused_mixed_OCR_pages": reused,
    }
    dump(meta, row)
    return row


rows = (
    {r["addendum_id"]: r for r in json.loads((F / "protocol_encoded_addenda.json").read_text())}
    if (F / "protocol_encoded_addenda.json").exists()
    else {}
)
completed = 0
with ThreadPoolExecutor(max_workers=8) as pool:
    futures = {pool.submit(extract, d): d for d in sorted(docs, key=lambda x: len(x["pages_requiring_OCR"]))}
    for future in as_completed(futures):
        row = future.result()
        rows[row["addendum_id"]] = row
        completed += 1
        pending = F / "protocol_encoded_addenda.tmp"
        dump(pending, sorted(rows.values(), key=lambda r: r["addendum_id"]))
        pending.replace(F / "protocol_encoded_addenda.json")
        print(
            "FONT OCR",
            "/",
            len(docs),
            "pages",
            len(row["page_numbers"]),
            "elapsed",
            round(time.monotonic() - started),
            flush=True,
        )
print(
    "FONT OCR COMPLETE",
    len(rows),
    "documents;",
    sum(len(r["page_numbers"]) for r in rows.values()),
    "pages; source images retained",
    flush=True,
)
