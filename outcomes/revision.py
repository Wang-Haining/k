"""Derive private sensitivity endpoints and publish only aggregate diagnostics."""

import calendar
import csv
import json
from collections import Counter, defaultdict
from datetime import date

from config import DATA_DIR, RESULTS_DIR
from outcomes.dates import interval
from outcomes.leadership import QUAL, name_compatible

RETRIEVAL = "2026-09-27"
STRATA = ("pre_early", "pre_legacy", "post")


def rows(relative, key):
    with (DATA_DIR / relative).open() as handle:
        data = list(csv.DictReader(handle))
    assert data and key in data[0], f"empty or missing {key}: {relative}"
    out = {r[key]: r for r in data}
    assert len(out) == len(data), f"duplicate keys in {relative}: {len(data) - len(out)}"
    return out


def write(path, data):
    assert data, f"no rows for {path.name}"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(data[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(data)
    print(f"{path.name}: {len(data)} rows")


def anniversary(value, years):
    d = date.fromisoformat(interval(value)[0])
    y = d.year + years
    return d.replace(year=y, day=min(d.day, calendar.monthrange(y, d.month)[1])).isoformat()


def main():
    people = rows("historical/person_analysis.csv", "blind_id")
    extended = rows("derived/historical_extended.csv", "blind_id")
    starts = rows("historical/persons.csv", "blind_id")
    strata = rows("derived/historical_reporting.csv", "blind_id")
    pairs = rows("historical/pairs.csv", "case_id")
    outcomes = rows("historical/pair_outcomes.csv", "case_id")
    seven = rows("derived/historical_seven_year.csv", "blind_id")
    assert people.keys() == extended.keys() == starts.keys() == strata.keys()
    assert pairs.keys() == outcomes.keys()
    features = json.loads((DATA_DIR / "instrument/trial_features.json").read_text())
    labels = {}
    for path in (DATA_DIR / "historical/leadership_labels").glob("*.json"):
        rec = json.loads(path.read_text())
        assert rec["status"] == "success", "unsuccessful historical label"
        labels[rec["case_id"]] = rec["label"]
    columns = (
        "k_id_field",
        "k_text",
        "k_none",
        "k_no_text",
        "new_no_text",
        "k_excl_covid",
        "new_excl_covid",
        "new_5y_registered",
        "new_7y_registered",
        "new_7y_reproduced",
    )
    person = {b: dict.fromkeys(columns, 0) for b in people}
    k_pairs, linked = [], {}
    cross = Counter()
    for cid, pair in pairs.items():
        b = pair["blind_id"]
        link = pair["k_link"]
        assert link in ("id_field", "text", "none"), "unknown grant-link category"
        p = people[b]
        eligible = p["mechanism"] == "K23" and extended[b]["besh_only_classifier"] == "0"
        if eligible and p["intent"] == "1" and link != "none":
            linked[cid] = pair
        sec = outcomes[cid]["secondary_pair"] == "True"
        pri = outcomes[cid]["primary_pair"] == "True"
        if not sec:
            assert not pri, "primary pair without secondary leadership"
            continue
        assert cid in labels, "qualifying pair lacks a leadership label"
        judgment = labels[cid]["k_relationship"]
        k = link != "none" or judgment == "original_K"
        assert pri == (link == "none" and judgment == "new_protocol"), "primary classification mismatch"
        v = person[b]
        if k:
            v[f"k_{link}"] = 1
            k_pairs.append(pair)
        v["k_no_text"] |= int(link == "id_field" or judgment == "original_K")
        v["new_no_text"] |= int(link != "id_field" and judgment == "new_protocol")
        noncovid = interval(pair["start_date"])[0][:4] not in ("2020", "2021")
        v["k_excl_covid"] |= int(k and noncovid)
        v["new_excl_covid"] |= int(pri and noncovid)
        if pri:
            submitted = features[pair["nct_id"]]["first_submitted"]
            assert submitted, "qualifying new trial lacks first-submitted date"
            for horizon in (5, 7):
                v[f"new_{horizon}y_registered"] |= int(submitted <= anniversary(starts[b]["start_date"], horizon))
            v["new_7y_reproduced"] = 1
        if eligible:
            cross[strata[b]["stratum"], p["intent"], link, judgment] += 1
    for b, v in person.items():
        assert int(any(v[f"k_{x}"] for x in ("id_field", "text", "none"))) == int(extended[b]["ktrial_direct"]), (
            "K-trial reconstruction mismatch"
        )
        assert v["k_excl_covid"] <= int(extended[b]["ktrial_direct"]), "COVID K endpoint not nested"
        assert v["new_excl_covid"] <= int(people[b]["primary"]), "COVID new endpoint not nested"

    # PI of record uses current registry fields, including candidates outside the five-year outcome window.
    pi = defaultdict(set)
    pi_records = Counter()
    seen = set()
    for line in (DATA_DIR / "historical/packets.jsonl").open():
        packet = json.loads(line)
        cid = packet["case_id"]
        if cid not in linked:
            continue
        seen.add(cid)
        pair = linked[cid]
        b, t = pair["blind_id"], packet["trial"]
        officials = [o for o in t["overall_officials"] if o["role"] == "PRINCIPAL_INVESTIGATOR" and o["name"]]
        rp = t["responsible_party"]
        if rp.get("type") not in ("PRINCIPAL_INVESTIGATOR", "SPONSOR_INVESTIGATOR"):
            rp = {}
        current = {
            "trial": {"overall_officials": officials, "responsible_party": rp},
            "historical_registry_snapshots": [],
            "protocol_excerpts": [],
        }
        named = bool(officials or rp.get("investigatorFullName"))
        category = "no_pi_named"
        if named:
            category = (
                "awardee"
                if name_compatible(starts[b]["first_name"], starts[b]["last_name"], current)
                else "other_person"
            )
        pi[b].add(category)
        pi_records[strata[b]["stratum"], category] += 1
    assert len(seen) == len(linked), f"missing linked packets: {len(linked) - len(seen)}"

    late_packets = {}
    for line in (DATA_DIR / "historical/seven_year_packets.jsonl").open():
        packet = json.loads(line)
        late_packets[packet["case_id"]] = packet
    late_labels = list((DATA_DIR / "historical/seven_year_labels/labels").glob("*.json"))
    assert len(late_labels) == len(late_packets) > 0, "seven-year packet/label counts differ"
    for path in late_labels:
        rec = json.loads(path.read_text())
        cid, lab = rec["case_id"], rec["label"]
        assert rec["status"] == "success" and rec["packet_sha256"] == late_packets[cid]["packet_sha256"], (
            "seven-year label provenance mismatch"
        )
        pair = pairs[cid]
        b = pair["blind_id"]
        start = starts[b]["start_date"]
        qualifies = (
            lab["identity"] == "same_person"
            and lab["role"] in QUAL
            and lab["scope"] == "applied"
            and pair["study_type"] == "INTERVENTIONAL"
            and pair["k_link"] == "none"
            and lab["k_relationship"] == "new_protocol"
            and name_compatible(starts[b]["first_name"], starts[b]["last_name"], late_packets[cid])
        )
        if qualifies:
            lo, hi = interval(pair["start_date"])
            assert anniversary(start, 5) < lo <= hi <= anniversary(start, 7), "late trial outside years five to seven"
            submitted = features[pair["nct_id"]]["first_submitted"]
            assert submitted, "qualifying late trial lacks first-submitted date"
            person[b]["new_7y_reproduced"] = 1
            person[b]["new_7y_registered"] |= int(submitted <= anniversary(start, 7))
    for b, old in seven.items():
        assert person[b]["new_7y_reproduced"] == int(old["new_trial_7y"]), "seven-year reconstruction mismatch"
        assert person[b]["new_5y_registered"] <= person[b]["new_7y_registered"] <= int(old["new_trial_7y"]), (
            "registration endpoint nesting mismatch"
        )
    write(DATA_DIR / "derived/revision_person.csv", [dict(blind_id=b, **v) for b, v in person.items()])

    public = RESULTS_DIR / "sensitivity"
    cells, pi_cells = [], []
    for stratum in STRATA:
        for intent in ("0", "1"):
            ids = [
                b
                for b, p in people.items()
                if p["mechanism"] == "K23"
                and p["intent"] == intent
                and extended[b]["besh_only_classifier"] == "0"
                and strata[b]["stratum"] == stratum
            ]
            assert ids, f"empty K23 cell: {stratum}, intent={intent}"
            for link in ("id_field", "text", "none"):
                n = sum(person[b][f"k_{link}"] for b in ids)
                cells.append(
                    dict(
                        stratum=stratum,
                        intent=intent,
                        component=link,
                        n=len(ids),
                        events=n,
                        share_pct=round(100 * n / len(ids), 2),
                    )
                )
            if intent == "1":
                for category in ("awardee", "other_person", "no_pi_named"):
                    n = sum(category in pi[b] for b in ids)
                    pi_cells.append(
                        dict(
                            stratum=stratum,
                            pi_of_record=category,
                            n_awardees=len(ids),
                            n_with_any_linked=sum(bool(pi[b]) for b in ids),
                            n_with_category=n,
                            share_pct=round(100 * n / len(ids), 2),
                            candidate_records=pi_records[stratum, category],
                        )
                    )
    write(public / "grant_link_cells.csv", cells)
    write(public / "grant_link_pi.csv", pi_cells)
    write(
        public / "grant_link_judgments.csv",
        [dict(stratum=s, intent=i, link=link, judgment=j, n_pairs=n) for (s, i, link, j), n in sorted(cross.items())],
    )

    reporting, reporting_cells = [], []
    for stratum in STRATA:
        selected = [
            p
            for p in k_pairs
            if people[p["blind_id"]]["mechanism"] == "K23"
            and people[p["blind_id"]]["intent"] == "1"
            and extended[p["blind_id"]]["besh_only_classifier"] == "0"
            and strata[p["blind_id"]]["stratum"] == stratum
        ]
        assert len({p["nct_id"] for p in selected}) == len(selected), "duplicate K trial within stratum"
        counts = Counter()
        for pair in selected:
            f = features[pair["nct_id"]]
            pcd = f["primary_completion"]
            counts["missing_pcd"] += int(not pcd)
            counts["unknown_pcd_passed"] += int(
                bool(pcd) and interval(pcd)[0] <= RETRIEVAL and f["status"] == "UNKNOWN"
            )
            terminated = (
                f["status"] == "TERMINATED"
                and f["enrollment_type"] == "ACTUAL"
                and f["enrollment"] is not None
                and f["enrollment"] > 0
            )
            due = bool(pcd) and anniversary(pcd, 1) <= RETRIEVAL and (f["status"] == "COMPLETED" or terminated)
            if not due:
                continue
            submitted = f["results_first_submitted"]
            ever = bool(submitted)
            within12 = ever and submitted <= anniversary(pcd, 1)
            counts["due"] += 1
            counts["terminated_due"] += int(terminated)
            counts["within12"] += int(within12)
            counts["ever_submitted"] += int(ever)
            reporting.append(
                dict(
                    stratum=stratum,
                    org_id=people[pair["blind_id"]]["org_id"],
                    within12=int(within12),
                    ever_submitted=int(ever),
                )
            )
        assert counts["due"] > 0, f"no due K trials in {stratum}"
        reporting_cells.append(
            dict(
                stratum=stratum,
                n_k_trials=len(selected),
                n_due=counts["due"],
                n_terminated_due=counts["terminated_due"],
                n_within12=counts["within12"],
                within12_pct=round(100 * counts["within12"] / counts["due"], 2),
                n_ever_submitted=counts["ever_submitted"],
                ever_submitted_pct=round(100 * counts["ever_submitted"] / counts["due"], 2),
                n_unknown_pcd_passed=counts["unknown_pcd_passed"],
                n_missing_pcd=counts["missing_pcd"],
            )
        )
    assert len(
        {
            p["nct_id"]
            for p in k_pairs
            if people[p["blind_id"]]["mechanism"] == "K23"
            and people[p["blind_id"]]["intent"] == "1"
            and extended[p["blind_id"]]["besh_only_classifier"] == "0"
        }
    ) == sum(r["n_k_trials"] for r in reporting_cells), "K trial appears in multiple strata"
    write(DATA_DIR / "derived/revision_reporting.csv", reporting)
    write(public / "reporting_trial_cells.csv", reporting_cells)
    print(
        f"Reconciled K outcomes: {len(people)} awardees; seven-year outcomes: {len(seven)} awardees; "
        f"free-text candidate links: {sum(p['k_link'] == 'text' for p in pairs.values())}; "
        f"due K23 trials: {len(reporting)}"
    )


if __name__ == "__main__":
    main()
