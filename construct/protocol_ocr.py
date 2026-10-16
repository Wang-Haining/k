"""Protocol ocr."""

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
R = F / "sources" / "mixed_ocr"
R.mkdir(exist_ok=True)
docs = [d for d in json.loads((F / "protocol_mixed_page_audit.json").read_text()) if d["pages_requiring_OCR"]]
sources = {s["url"]: s for s in json.loads((F / "protocol_sources.json").read_text())}
assert docs and len(docs) == len({d["url"] for d in docs}), (
    "Required source invariant failed; inspect the private input locally."
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
    for n in pages:
        target = folder / f"page-{n:04d}"
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
    target = F / "packets" / f"protocol_{stem}.mixed.ocr.txt"
    target.write_text(text)
    row = {
        "nct_id": d["nct_id"],
        "source_url": d["url"],
        "document_date_metadata": sources[d["url"]]["document_date"],
        "local_text": str(target),
        "image_pages": images,
        "page_numbers": pages,
        "method": (
            "tesseract_eng_200dpi; low-text pages with large images or complex drawing c"
            "ontent; verify decisive PI/date text visually"
        ),
        "pdf_sha256": digest,
        "text_sha256": hashlib.sha256(text.encode()).hexdigest(),
        "addendum_id": stem + "_MIXED_OCR",
    }
    dump(meta, row)
    return row


rows = (
    {r["addendum_id"]: r for r in json.loads((F / "protocol_mixed_addenda.json").read_text())}
    if (F / "protocol_mixed_addenda.json").exists()
    else {}
)
completed = 0
with ThreadPoolExecutor(max_workers=8) as pool:
    futures = {pool.submit(extract, d): d for d in sorted(docs, key=lambda x: len(x["pages_requiring_OCR"]))}
    for future in as_completed(futures):
        row = future.result()
        rows[row["addendum_id"]] = row
        completed += 1
        pending = F / "protocol_mixed_addenda.tmp"
        dump(pending, sorted(rows.values(), key=lambda r: r["addendum_id"]))
        pending.replace(F / "protocol_mixed_addenda.json")
        if completed % 10 == 0:
            print(
                "MIXED OCR",
                "/",
                len(docs),
                "documents;",
                sum(len(r["page_numbers"]) for r in rows.values()),
                "pages; elapsed seconds",
                round(time.monotonic() - started),
                flush=True,
            )
print(
    "MIXED OCR COMPLETE",
    len(rows),
    "documents;",
    sum(len(r["page_numbers"]) for r in rows.values()),
    "pages; PDFs and rendered images retained",
    flush=True,
)
