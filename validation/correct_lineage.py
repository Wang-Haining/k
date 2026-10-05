"Impute lineage status within validation cells and bootstrap by institution."

import csv
import json
import random
from collections import Counter, defaultdict

from config import DATA_DIR, LINEAGE_CORRECTION_SEED, RESULTS_DIR
from outcomes.reporting import stratum
from validation import score as E

HD, RV, HU = (DATA_DIR / "historical", DATA_DIR / "derived", DATA_DIR / "ratings")
DEV = {"extension", "same_approach_new_question"}
B = 2000


def main():
    base = DATA_DIR / "validation"
    a, _, dis = E.ratings(base)
    ref = E.reference(base, a, dis)
    model = {r["item"]: r["lineage"] in DEV for r in csv.DictReader((HU / "lineage_labels.csv").open())}
    cnt = defaultdict(lambda: [0, 0])
    for r in csv.DictReader((base / "key_private.csv").open()):
        if r["module"] == "lineage":
            src = json.loads(r["instrument_label"])["source_item"]
            cnt[r["stratum"], r["instrument_state"], model[src]][int(ref["lineage", r["item"]]["lineage"] in DEV)] += 1
    pairs = list(csv.DictReader((HU / "lineage_sample_private.csv").open()))
    pa = {r["blind_id"]: r for r in csv.DictReader((HD / "person_analysis.csv").open())}
    extended = {r["blind_id"]: r for r in csv.DictReader((RV / "historical_extended.csv").open())}
    ids = [
        b
        for b in pa
        if pa[b]["mechanism"] == "K23" and pa[b]["intent"] == "1" and (extended[b]["besh_only_classifier"] == "0")
    ]
    S = {b: stratum(pa[b]) for b in ids}
    by = defaultdict(list)
    for p in pairs:
        if p["blind_id"] in S:
            by[p["blind_id"]].append((p["period"], p["has_ktrial"], model[p["item"]]))
    org = defaultdict(list)
    for b in ids:
        org[pa[b]["org_id"]].append(b)
    keys, rng = (list(org), random.Random(LINEAGE_CORRECTION_SEED))

    def draw():
        th = {}
        for c, (n0, n1) in cnt.items():
            pr = (0.5, 0.01) if c[2] else (0.01, 0.5)
            th[c] = rng.betavariate(n1 + pr[0], n0 + pr[1])
        return th

    def stats(sample, th):
        dev, share = (Counter(), defaultdict(lambda: [0, 0]))
        n = Counter(S[b] for b in sample)
        for b in sample:
            hits = [rng.random() < th[c] for c in by.get(b, [])]
            dev[S[b]] += any(hits)
            share[S[b]][0] += sum(hits)
            share[S[b]][1] += len(hits)
        pct = {s: 100 * dev[s] / n[s] for s in n}
        out = {f"dev_{s}": pct[s] for s in pct}
        out.update({f"diff_{ref}": pct["post"] - pct[ref] for ref in ("pre_early", "pre_legacy")})
        out.update({f"pairshare_{s}": 100 * v[0] / v[1] for s, v in share.items()})
        return out

    reps = []
    for _ in range(B):
        smp = [b for _ in keys for b in org[rng.choice(keys)]]
        reps.append(stats(smp, draw()))

    def q(xs, p):
        return sorted(xs)[int(p * (len(xs) - 1))]

    rows = []
    for k in reps[0]:
        xs = [r[k] for r in reps if k in r]
        rows.append(
            {
                "quantity": k,
                "estimate": round(sum(xs) / len(xs), 1),
                "lo": round(q(xs, 0.025), 1),
                "hi": round(q(xs, 0.975), 1),
                "reps": len(xs),
            }
        )
    rows.append(
        {
            "quantity": "validation_cells",
            "estimate": json.dumps({"|".join(map(str, c)): v for c, v in sorted(cnt.items())}),
            "lo": "",
            "hi": "",
            "reps": "",
        }
    )
    E.write_csv(RESULTS_DIR / "validation" / "lineage_corrected.csv", rows)


if __name__ == "__main__":
    main()
    print("validation/correct_lineage.py: complete")
