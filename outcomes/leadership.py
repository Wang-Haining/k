"Combine frozen leadership labels, timing, grant links, and the name guard."

import csv
import json

from config import DATA_DIR
from outcomes.names import TITLES, norm

INSTRUMENT_DIR = DATA_DIR / "instrument"
LABELS = INSTRUMENT_DIR / "qwen" / "leadership_labels"
QUAL = {"overall_PI", "responsible_party_PI", "sponsor_investigator", "protocol_named_PI"}


def close(a, b):
    if a == b or ((len(a) == 1 or len(b) == 1) and a[0] == b[0]):
        return True
    if min(len(a), len(b)) < 4 or abs(len(a) - len(b)) > 1:
        return False
    if len(a) == len(b):
        return sum((x != y for x, y in zip(a, b, strict=False))) == 1
    s, label = sorted((a, b), key=len)
    return any(label[:i] + label[i + 1 :] == s for i in range(len(label)))


def name_compatible(first, last, packet):
    sur = {w for w in norm(last).split() if len(w) >= 2}
    given = norm(first).split()
    t = packet["trial"]
    texts = [o["name"] for o in t["overall_officials"]] + [t["responsible_party"].get("investigatorFullName", "")]
    texts += [r["name"] for r in packet["historical_registry_snapshots"]] + [
        e["excerpt"] for e in packet["protocol_excerpts"]
    ]
    for text in filter(None, texts):
        toks = norm(text).split()
        for i, w in enumerate(toks):
            if w in sur:
                near = [
                    x for j, x in enumerate(toks[max(0, i - 4) : i + 5], max(0, i - 4)) if j != i and x not in TITLES
                ]
                if any(close(x, g) for x in near for g in given):
                    return True
    return False


def main():
    screen = {r["case_id"]: r for r in csv.DictReader((INSTRUMENT_DIR / "pair_screen.csv").open())}
    key = {
        r["blind_id"]: {k: r[k] for k in ("first_name", "last_name", "start_date")}
        for r in json.loads((DATA_DIR / "contemporaneous" / "cohort_key_private.json").read_text())
    }
    rows = []
    for line in (INSTRUMENT_DIR / "qwen" / "packets_all.jsonl").open():
        p = json.loads(line)
        cid, s = (p["case_id"], screen[p["case_id"]])
        rec = json.loads((LABELS / f"{cid}.json").read_text())
        assert rec["status"] == "success" and rec["packet_sha256"] == p["packet_sha256"], cid
        label, k = (rec["label"], key[s["blind_id"]])
        guard = name_compatible(k["first_name"], k["last_name"], p)
        same = label["identity"] == "same_person" and guard
        qual = same and label["role"] in QUAL
        interventional = s["study_type"] == "INTERVENTIONAL"
        secondary = qual and label["scope"] == "applied" and interventional and (s["window"] == "inside")
        primary = secondary and s["k_link"] == "none" and (label["k_relationship"] == "new_protocol")
        preK = qual and label["scope"] == "applied" and interventional and (s["window"] == "pre_K")
        timing_unresolved = (
            qual
            and label["scope"] == "applied"
            and interventional
            and (s["window"] in ("boundary_uncertain", "missing"))
        )
        rows.append(
            {
                "case_id": cid,
                "blind_id": s["blind_id"],
                "nct_id": s["nct_id"],
                "start_date": s["start_date"],
                "window": s["window"],
                "k_link": s["k_link"],
                "identity": label["identity"],
                "name_guard": guard,
                "role": label["role"],
                "role_source": label["role_source"],
                "scope": label["scope"],
                "k_relationship": label["k_relationship"],
                "secondary_pair": secondary,
                "primary_pair": primary,
                "preK_pair": preK,
                "timing_unresolved_pair": timing_unresolved,
                "flag_withdrawn_zero": s["flag_withdrawn_zero"],
                "flag_start_conflict": s["flag_start_conflict"],
                "primary_purpose": s["primary_purpose"],
            }
        )
    by = {}
    for r in rows:
        by.setdefault(r["blind_id"], []).append(r)
    persons = []
    for b in sorted(key):
        rs = by.get(b, [])

        def state(f, rs=rs):
            return (
                "event"
                if any(r[f] for r in rs)
                else "unresolved"
                if any(r["timing_unresolved_pair"] for r in rs)
                else "not_documented"
            )

        persons.append(
            {
                "blind_id": b,
                "secondary": state("secondary_pair"),
                "primary": state("primary_pair"),
                "first_secondary_start": min((r["start_date"] for r in rs if r["secondary_pair"]), default=""),
                "first_primary_start": min((r["start_date"] for r in rs if r["primary_pair"]), default=""),
                "preK_PI": any(r["preK_pair"] for r in rs),
                "n_secondary_trials": sum(r["secondary_pair"] for r in rs),
            }
        )
    for name, data in (("instrument_pair_outcomes.csv", rows), ("instrument_person_outcomes.csv", persons)):
        with (INSTRUMENT_DIR / name).open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(data[0]), lineterminator="\n")
            w.writeheader()
            w.writerows(data)
            print("CSV rows:", len(data))


if __name__ == "__main__":
    main()
    print("outcomes/leadership.py: complete")
