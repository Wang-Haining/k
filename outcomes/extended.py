"Derive private leadership, reporting, prior-award, and funding endpoints."

import csv
import glob
import json
import re
from datetime import date, timedelta
from pathlib import Path

from config import DATA_DIR
from outcomes.dates import interval
from outcomes.leadership import QUAL, name_compatible

INSTRUMENT_DIR, HD, OUT = (DATA_DIR / "instrument", DATA_DIR / "historical", DATA_DIR / "derived")
DUE = "2025-09-27"
R01EQ, TRIALGRANT = ({"R01", "R37", "R35", "DP2"}, {"R61", "R33", "UG3", "UH3"})
R01NIH = {"R01", "R37", "R56", "RF1", "RL1", "U01", "DP1", "DP2", "DP5"}


def nih_r01eq(e):
    return e["code"] in R01NIH or (e["code"] == "R35" and e.get("ic") in ("GM", "HG"))


KTRIALS = []
GRANT = re.compile("([A-Z]{2})(\\d{6})")


def plus_days(d, n):
    return (date.fromisoformat(interval(d)[0]) + timedelta(days=n)).isoformat()


def timely(s, f):
    return bool(f["first_submitted"]) and f["first_submitted"][:10] <= plus_days(s["start_date"], 365)


def serials(ids):
    return {"".join(m) for x in ids for m in GRANT.findall(re.sub("[\\s-]", "", x.upper()))}


RESEARCH = re.compile("^(R|U|P|DP)\\d")


def prior_awards():
    out = {}
    for f in glob.glob(str(DATA_DIR / "reporter/contemporaneous" / "*.json")) + glob.glob(
        str(DATA_DIR / "reporter/historical" / "*.json")
    ):
        for r in json.loads(Path(f).read_text())["response"]["results"]:
            code, st = (r.get("activity_code") or "", (r.get("project_start_date") or "")[:10])
            if not st or code in ("K08", "K23"):
                continue
            for p in r["principal_investigators"]:
                d = out.setdefault(p["profile_id"], {"any": [], "research": []})
                d["any"].append(st)
                if RESEARCH.match(code):
                    d["research"].append(st)
    return out


prior_starts = {}


def person_grants():
    g = {}
    for f in glob.glob(str(DATA_DIR / "reporter/contemporaneous" / "*.json")) + glob.glob(
        str(DATA_DIR / "reporter/historical" / "*.json")
    ):
        for r in json.loads(Path(f).read_text())["response"]["results"]:
            for p in r["principal_investigators"]:
                g.setdefault(p["profile_id"], set()).update(serials([r["core_project_num"] or ""]))
    return g


def years(d0, d1):
    return (date.fromisoformat(interval(d1)[0]) - date.fromisoformat(d0)).days / 365.25


def person_outcomes(pairs, labels, packets, feats, key, funding, grants, funding_nih=None, tag=""):
    by = {}
    for s in pairs:
        cid = s["case_id"]
        k = key[s["blind_id"]]
        lab = labels.get(cid)
        if lab is None:
            by.setdefault(s["blind_id"], [])
            continue
        guard = name_compatible(k["first_name"], k["last_name"], packets[cid]) if cid in packets else False
        f = feats[s["nct_id"]]
        same = lab["identity"] == "same_person" and guard
        interv, inside = (s["study_type"] == "INTERVENTIONAL", s["window"] == "inside")
        qual = same and lab["role"] in QUAL and interv and inside
        linked = s["k_link"] != "none"
        new = qual and lab["scope"] == "applied" and (not linked) and (lab["k_relationship"] == "new_protocol")
        kq = (
            same
            and lab["role"] in QUAL
            and interv
            and (lab["scope"] == "applied")
            and (linked or lab["k_relationship"] == "original_K")
        )
        if kq and s["window"] in ("inside", "pre_K"):
            KTRIALS.append(
                {
                    "analysis": tag,
                    "blind_id": s["blind_id"],
                    "nct_id": s["nct_id"],
                    "start_date": s["start_date"],
                    "window": s["window"],
                    "k_grant_linked": int(linked),
                }
            )
        due = new and f["status"] == "COMPLETED" and f["primary_completion"] and (f["primary_completion"][:10] <= DUE)
        by.setdefault(s["blind_id"], []).append(
            {
                "ktrial_direct": qual
                and lab["scope"] == "applied"
                and (linked or lab["k_relationship"] == "original_K"),
                "ktrial_direct_fdaaa": qual
                and lab["scope"] == "applied"
                and (linked or lab["k_relationship"] == "original_K")
                and (s.get("fdaaa_like", f.get("fdaaa_like")) in ("True", True)),
                "informative_strict": new
                and f["randomized"]
                and (f["n_sites"] >= 3 or (f["enrollment"] or 0) >= 300 or "PHASE3" in f["phases"])
                and (f["status"] not in ("TERMINATED", "WITHDRAWN")),
                "new_trial_due": due,
                "new_trial_due_with_results": due and f["has_results"],
                "primary_nihdef": qual
                and lab["scope"] in ("applied", "BESH_only")
                and (not linked)
                and (lab["k_relationship"] == "new_protocol"),
                "primary_late": new and years(k["start_date"], s["start_date"]) >= 3,
                "nonpi_multisite": same
                and lab["role"] == "nonqualifying_role"
                and (lab["scope"] == "applied")
                and interv
                and inside
                and (f["n_sites"] >= 3),
                "ktrial_timely": qual
                and lab["scope"] == "applied"
                and (linked or lab["k_relationship"] == "original_K")
                and timely(s, f),
                "primary_timely": new and timely(s, f),
                "new_trial_due_results12": due
                and bool(f["results_first_submitted"])
                and (f["results_first_submitted"][:10] <= plus_days(f["primary_completion"], 365)),
                "nih_new_trial": new and bool(serials(f["nih_grant_ids"])),
                "nih_new_trial_own_grant": new and bool(serials(f["nih_grant_ids"]) & grants.get(k["pi_id"], set())),
                "ktrial_any_start": kq and s["window"] in ("inside", "pre_K"),
                "ktrial_grant_linked": kq and linked and inside,
                "ktrial_judged_unlinked": kq and (not linked) and inside,
                "primary_judgment_only": qual
                and lab["scope"] == "applied"
                and (lab["k_relationship"] == "new_protocol"),
                "primary_link_only": qual and lab["scope"] == "applied" and (not linked),
                "led_nct": s["nct_id"] if qual and lab["scope"] == "applied" else "",
            }
        )
    rows = []
    for b, k in key.items():
        ps = by.get(b, [])
        ev = funding.get(b, [])

        def yrs(e, k=k):
            return years(k["start_date"], e["start"])

        row = {"blind_id": b}
        for o in (
            "ktrial_direct",
            "ktrial_direct_fdaaa",
            "informative_strict",
            "new_trial_due",
            "new_trial_due_with_results",
            "primary_nihdef",
            "primary_late",
            "nonpi_multisite",
            "ktrial_timely",
            "primary_timely",
            "new_trial_due_results12",
            "nih_new_trial",
            "nih_new_trial_own_grant",
            "ktrial_any_start",
            "ktrial_grant_linked",
            "ktrial_judged_unlinked",
            "primary_judgment_only",
            "primary_link_only",
        ):
            row[o] = int(any(p[o] for p in ps))
        row["n_trials_led"] = len({p["led_nct"] for p in ps if p["led_nct"]})
        row["two_plus_trials"] = int(row["n_trials_led"] >= 2)
        row["prior_nih_pi_award"] = int(
            any(g < k["start_date"] for g in prior_starts.get(k["pi_id"], {}).get("any", []))
        )
        row["prior_research_grant"] = int(
            any(g < k["start_date"] for g in prior_starts.get(k["pi_id"], {}).get("research", []))
        )
        row["R01eq_5y"] = int(any(e["code"] in R01EQ and yrs(e) <= 5 for e in ev))
        row["R01eq_7y"] = int(any(e["code"] in R01EQ and yrs(e) <= 7 for e in ev))
        row["R01eq_or_trialgrant_5y"] = int(any(e["code"] in R01EQ | TRIALGRANT and yrs(e) <= 5 for e in ev))
        evn = (funding_nih or {}).get(b, [])
        row["R01nih_5y"] = int(any(nih_r01eq(e) and yrs(e) <= 5 for e in evn))
        row["R01nih_7y"] = int(any(nih_r01eq(e) and yrs(e) <= 7 for e in evn))
        row["R01nih_R35_5y"] = int(any((nih_r01eq(e) or e["code"] == "R35") and yrs(e) <= 5 for e in evn))
        row["R01nih_or_trialgrant_5y"] = int(
            any((nih_r01eq(e) or e["code"] in TRIALGRANT) and yrs(e) <= 5 for e in evn)
        )
        row["followup_7y_complete"] = int(
            date.fromisoformat(k["start_date"]).replace(year=int(k["start_date"][:4]) + 7) <= date(2026, 9, 27)
        )
        rows.append(row)
    return rows


def load_labels(d):
    return {p.stem: json.loads(p.read_text())["label"] for p in Path(d).glob("*.json")}


def main():
    feats = json.loads((INSTRUMENT_DIR / "trial_features.json").read_text())
    funding = json.loads((OUT / "funding_events.json").read_text())
    funding_nih = json.loads((OUT / "nih_funding_events.json").read_text())
    post = {
        r["blind_id"]: r for r in json.loads((DATA_DIR / "contemporaneous" / "cohort_key_private.json").read_text())
    }
    pre = {r["blind_id"]: r for r in json.loads((HD / "cohort_key_private.json").read_text())}
    screen = list(csv.DictReader((INSTRUMENT_DIR / "pair_screen.csv").open()))
    for s in screen:
        s["fdaaa_like"] = ""
    pk = {
        json.loads(label)["case_id"]: json.loads(label)
        for label in (INSTRUMENT_DIR / "qwen" / "packets_all.jsonl").open()
    }
    grants = person_grants()
    prior_starts.update(prior_awards())
    m = person_outcomes(
        screen,
        load_labels(INSTRUMENT_DIR / "qwen" / "leadership_labels"),
        pk,
        feats,
        post,
        funding,
        grants,
        funding_nih,
        "main",
    )
    bh = list(csv.DictReader((HD / "pairs.csv").open()))
    lab = load_labels(HD / "leadership_labels")
    bpk = {}
    for label in (HD / "reviewed_packets.jsonl").open():
        p = json.loads(label)
        bpk[p["case_id"]] = p
    h = person_outcomes(bh, lab, bpk, feats, {**post, **pre}, funding, grants, funding_nih, "historical")
    intent = {p.stem: json.loads(p.read_text())["label"] for p in (HD / "intent_labels").glob("*.json")}
    for r in h:
        r["besh_only_classifier"] = int(intent[r["blind_id"]]["human_intervention_scope"] == "BESH_only")
    for name, rows in (("contemporaneous_extended.csv", m), ("historical_extended.csv", h)):
        with (OUT / name).open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
            w.writeheader()
            w.writerows(rows)
            print("CSV rows:", len(rows))
    with (OUT / "ktrial_pairs.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(KTRIALS[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(KTRIALS)
        print("CSV rows:", len(KTRIALS))


if __name__ == "__main__":
    main()
    print("outcomes/extended.py: complete")
