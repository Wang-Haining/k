"""Export per-awardee human reference states for the measurement-error correction.

Writes two private files under DATA_DIR/validation:
- reference_dossier_private.csv: one row per sampled awardee dossier with its sampling cell, the instrument's
  joint K-trial/new-trial state, and the human joint state under four reference rules (primary, swapped overlap
  rater, rater A for all double-rated dossiers, rater B for all double-rated dossiers). Unclear states are blank.
- reference_intent_private.csv: one row per sampled abstract with the instrument intent call and the human intent.
"""

import csv
import json

from config import DATA_DIR
from validation import score as E
from validation.pool import RATERS, additional

BASE = DATA_DIR / "validation"
AW = ("led_K_trial", "led_new_trial")


def joint(row):
    k, p = row["led_K_trial"], row["led_new_trial"]
    if "unclear" in (k, p):
        return ""
    return f"k{int(k == 'yes')}p{int(p == 'yes')}"


def main():
    a, b, dis = E.ratings(BASE)
    adjudicated = E.reference(BASE, a, dis)
    raw = {"rater_a": a, "rater_b": b}
    extra = {r: additional(r) for r in RATERS}
    assignment = {
        r["item"]: r for r in E.csv_rows(BASE / "assignment_private.csv", ("item", "set", "raters", "reference_rater"))
    }
    key = E.csv_rows(
        BASE / "key_private.csv",
        ("module", "item", "blind_id", "stratum", "intent", "instrument_state", "instrument_label"),
    )
    rows = []
    for k in key:
        if k["module"] != "dossier":
            continue
        item = k["item"]
        label = json.loads(k["instrument_label"])
        own = f"k{int(label['ktrial_direct'])}p{int(label['primary'])}"
        if int(item[1:]) <= 70:
            ref = {
                "ref_primary": joint(adjudicated["dossier", item]),
                "ref_swap": joint(adjudicated["dossier", item]),
                "ref_rater_a": joint(raw["rater_a"]["dossier", item]),
                "ref_rater_b": joint(raw["rater_b"]["dossier", item]),
            }
        else:
            asg = assignment[item]
            primary = asg["reference_rater"]
            if asg["set"] == "single":
                one = joint(extra[primary]["dossier_awardees", item])
                ref = dict.fromkeys(("ref_primary", "ref_swap", "ref_rater_a", "ref_rater_b"), one)
            else:
                other = next(r for r in RATERS if r != primary)
                ref = {
                    "ref_primary": joint(extra[primary]["dossier_awardees", item]),
                    "ref_swap": joint(extra[other]["dossier_awardees", item]),
                    "ref_rater_a": joint(extra["rater_a"]["dossier_awardees", item]),
                    "ref_rater_b": joint(extra["rater_b"]["dossier_awardees", item]),
                }
        rows.append(
            {
                "blind_id": k["blind_id"],
                "stratum": k["stratum"],
                "intent": k["intent"],
                "instrument_cell": k["instrument_state"],
                "instrument_state": own,
                **ref,
            }
        )
    with (BASE / "reference_dossier_private.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    ikey = E.load_key(BASE / "initial_key.csv", a)
    intent_rows = []
    for idx, k in ikey.items():
        if idx[0] != "intent":
            continue
        human = adjudicated[idx]["intent"]
        intent_rows.append(
            {
                "blind_id": k["blind_id"],
                "stratum": k["stratum"],
                "call": int(k["label"]["own_trial_planned"] in (1, "1")),
                "human_intent": "" if human == "unclear" else int(human == "own_trial_planned"),
            }
        )
    with (BASE / "reference_intent_private.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(intent_rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(intent_rows)
    print("reference states:", len(rows), "dossiers;", len(intent_rows), "abstracts")


if __name__ == "__main__":
    main()
    print("validation/reference.py: complete")
