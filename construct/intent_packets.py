"""Intent packets."""

import hashlib
import json

from config import DATA_DIR
from construct.packet_fields import mask

post = json.loads((DATA_DIR / "contemporaneous/cohort_key_private.json").read_text())
pre = json.loads((DATA_DIR / "historical/cohort_key_private.json").read_text())
out = DATA_DIR / "historical/intent_packets.jsonl"
with out.open("w") as f:
    for r in post + pre:
        p = {"case_id": r["blind_id"], "K_title": mask(r["title"]), "K_abstract": mask(r["abstract"])[:6000]}
        p["packet_sha256"] = hashlib.sha256(json.dumps(p, sort_keys=True).encode()).hexdigest()
        f.write(json.dumps(p, ensure_ascii=False) + "\n")
print("intent packets:", len(post) + len(pre))
