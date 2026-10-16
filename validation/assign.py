"Assign additional dossiers to neutral raters with a randomized overlap set."

import csv
import random

from config import DOSSIER_ASSIGNMENT_SEED
from validation.expand import BANNER, sheet_rows
from validation.sample import OUT, RATERS, write_book

N_OVERLAP = 40


def main():
    rng = random.Random(DOSSIER_ASSIGNMENT_SEED)
    full = {r: sheet_rows(OUT / "expand" / f"rating_{r}.xlsx") for r in RATERS}
    new = sorted(
        {row["item"] for row in full[RATERS[0]]["dossier_awardees"] if int(row["item"][1:]) > 70},
        key=lambda s: int(s[1:]),
    )
    assert len(new) == 210, len(new)
    overlap = set(rng.sample(new, N_OVERLAP))
    rest = [i for i in new if i not in overlap]
    rng.shuffle(rest)
    half = len(rest) // 2
    own = {RATERS[0]: set(rest[:half]), RATERS[1]: set(rest[half:])}
    reference = {i: rng.choice(RATERS) for i in sorted(overlap, key=lambda s: int(s[1:]))}
    with (OUT / "assignment_private.csv").open("w", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["item", "set", "raters", "reference_rater"])
        for i in new:
            if i in overlap:
                w.writerow([i, "overlap", "+".join(RATERS), reference[i]])
            else:
                r = next(r for r in RATERS if i in own[r])
                w.writerow([i, "single", r, r])
    print("assigned:", len(new), "overlap:", len(overlap))
    out = OUT / "additional"
    out.mkdir(exist_ok=True)
    for r in RATERS:

        def keep(item, r=r):
            return int(item.split(".")[0][1:]) <= 70 or item.split(".")[0] in overlap | own[r]

        s = full[r]
        dossiers = [x for x in s["dossier_awardees"] if keep(x["item"])]
        dossier_trials = [x for x in s["dossier_trials"] if keep(x["trial"])]
        write_book(
            out / f"rating_{r}.xlsx", r, [], dossiers, dossier_trials, s["intent"], s["boundary"], s["lineage"], BANNER
        )
        sum(int(x["item"][1:]) > 70 for x in dossiers)


if __name__ == "__main__":
    main()
    print("validation/assign.py: complete")
