"""Write masked baseline abstract packets in the frozen random order."""

import json
import random

from config import COHORT_SEED, DATA_DIR
from construct.packet_fields import mask
from construct.reporter import dump


def main():
    key = json.loads((DATA_DIR / "contemporaneous/cohort_key_private.json").read_text())
    order = list(key)
    random.Random(COHORT_SEED).shuffle(order)
    manifest = []
    for offset in range(0, len(order), 20):
        rows = [{k: r[k] for k in ("blind_id", "title", "abstract", "source")} for r in order[offset : offset + 20]]
        for row in rows:
            row["title"] = mask(row["title"])
            row["abstract"] = mask(row["abstract"])
        name = f"baseline_{offset // 20 + 1:03d}.json"
        dump(DATA_DIR / "contemporaneous/packets" / name, rows)
        manifest.append({"packet": name, "n": len(rows), "blind_ids": [r["blind_id"] for r in rows]})
    dump(DATA_DIR / "contemporaneous/baseline_manifest.json", manifest)
    print("baseline people:", len(key), "packets:", len(manifest))


if __name__ == "__main__":
    main()
