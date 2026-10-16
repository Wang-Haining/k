"""Leadership packets."""

import csv
import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path

from config import DATA_DIR
from construct.packet_fields import clip, trial_block

F, INSTRUMENT = (DATA_DIR / "contemporaneous", DATA_DIR / "instrument")
QD = INSTRUMENT / "qwen"
ROLE_WORDS = re.compile(
    (
        "principal investigator|\\bP\\.?I\\.?\\b|sponsor[- ]investigator|study chair|stu"
        "dy director|overall (?:study )?(?:chair|investigator)|protocol chair|lead i"
        "nvestigator"
    ),
    re.I,
)
SNIPPET_CAP, DOC_CAP = (6000, 2500)


def protocol_texts():
    misassociated = {
        f["article_source"] for f in json.loads((F / "protocol_publication_association_flags.json").read_text())
    }

    docs = defaultdict(list)
    for r in json.loads((F / "protocol_sources.json").read_text()):
        if r.get("local_text") and r.get("status") == "text_available":
            docs[r["nct_id"]].append((f"protocol document {r.get('document_date', '')}", r["local_text"]))
    for name, label in (
        ("protocol_mixed_addenda.json", "protocol OCR pages"),
        ("protocol_encoded_addenda.json", "protocol OCR pages"),
        ("protocol_visual_addenda.json", "protocol OCR pages"),
        ("protocol_publication_addenda.json", "published protocol"),
    ):
        for r in json.loads((F / name).read_text()):
            if r.get("local_text") and r["local_text"] not in misassociated:
                docs[r["nct_id"]].append((label, r["local_text"]))
    return docs


def snippets(paths, surname):
    out, total = ([], 0)
    sur = re.compile("\\b" + re.escape(surname) + "\\b", re.I) if surname else None
    for label, path in paths:
        p = Path(path)
        text = p.read_text(errors="replace")
        if text.lstrip().startswith("{"):
            text = json.dumps(json.loads(text), ensure_ascii=False)
        lines = [line.strip() for line in re.split("\\\\n|\\n", text) if line.strip()]
        keep = sorted(
            {
                j
                for i, line in enumerate(lines)
                if sur and sur.search(line) or ROLE_WORDS.search(line)
                for j in (i - 1, i, i + 1)
                if 0 <= j < len(lines)
            }
        )
        if not keep:
            continue
        body = clip(" | ".join(lines[j] for j in keep), DOC_CAP)
        if total + len(body) > SNIPPET_CAP:
            break
        out.append({"source": label, "excerpt": body})
        total += len(body)
    return out


def aact_rows():
    rows = defaultdict(list)
    for a in json.loads((F / "historical_registry_addenda.json").read_text()):
        t = json.loads(Path(a["local_text"]).read_text()).get("verbatim_table_rows", {})
        for o in t.get("overall_officials", []):
            rows[a["nct_id"]].append(
                {
                    "snapshot": a["snapshot_date"],
                    "table": "overall_officials",
                    "name": o.get("name", ""),
                    "role": o.get("role", ""),
                    "affiliation": o.get("affiliation", ""),
                }
            )
        for o in t.get("responsible_parties", []):
            rows[a["nct_id"]].append(
                {
                    "snapshot": a["snapshot_date"],
                    "table": "responsible_parties",
                    "name": o.get("name", ""),
                    "role": o.get("responsible_party_type", ""),
                    "affiliation": o.get("affiliation") or o.get("organization") or "",
                }
            )
    return rows


def build_all():
    pairs = {r["case_id"]: r for r in csv.DictReader((INSTRUMENT / "pair_screen.csv").open())}
    orgs = {r["blind_id"]: r["orgs"] for r in json.loads((INSTRUMENT / "person_orgs.json").read_text())}
    docs, hist = (protocol_texts(), aact_rows())
    people = json.loads((INSTRUMENT / "trial_people.json").read_text())
    QD.mkdir(parents=True, exist_ok=True)
    n = 0
    with (QD / "packets_all.jsonl").open("w") as f:
        for c in sorted(json.loads((F / "review_cases.json").read_text()), key=lambda c: (c["blind_id"], c["case_id"])):
            t = trial_block(c, pairs[c["case_id"]])
            for k in ("screen", "ask", "evidence_sha256"):
                t.pop(k)
            t.update({k: people[t["nct_id"]][k] for k in ("overall_officials", "responsible_party")})
            nct = t["nct_id"]
            packet = {
                "case_id": c["case_id"],
                "awardee": {
                    "name": c["awardee"],
                    "K_core_project_num": c["K_core_project_num"],
                    "K_start": c["K_start"],
                    "K_window_end": c["end_5y"],
                    "K_institution": c["K_institution"],
                    "NIH_organizations": orgs[c["blind_id"]],
                    "K_title": c["K_title"],
                    "K_abstract": clip(c["K_abstract"], 4000),
                },
                "trial": t,
                "historical_registry_snapshots": hist.get(nct, [])[:20],
                "protocol_excerpts": snippets(docs.get(nct, []), c["last_name"]),
            }
            packet["packet_sha256"] = hashlib.sha256(json.dumps(packet, sort_keys=True).encode()).hexdigest()
            f.write(json.dumps(packet, ensure_ascii=False) + "\n")
            n += 1
    print("leadership packets:", n)


if __name__ == "__main__":
    build_all()
