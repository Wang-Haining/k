"""Assemble baseline eligibility from frozen independent abstract annotations."""

import json
from collections import Counter

from config import DATA_DIR
from construct.reporter import dump, table

F = DATA_DIR / "contemporaneous"
intent = {"own_trial_planned", "mentor_led_trial_explicit", "other_research", "unclear"}
scope = {"applied", "BESH_only", "mixed_applied_BESH", "no_human_intervention", "unclear"}


def read_labels(pattern, packet_prefix):
    result = {}
    for path in sorted((F / "labels").glob(pattern)):
        number = path.stem.rsplit("_", 1)[1]
        source = json.loads((F / "packets" / f"{packet_prefix}_{number}.json").read_text())
        rows = json.loads(path.read_text())
        assert len(rows) == len(source), "Baseline annotation invariant failed; inspect the private source locally."
        assert [r["blind_id"] for r in rows] == [r["blind_id"] for r in source], (
            "Baseline annotation invariant failed; inspect the private source locally."
        )
        for r, s in zip(rows, source, strict=False):
            assert r["blind_id"] not in result and r["reviewer_id"] and r["rationale"], (
                "Baseline annotation invariant failed; inspect the private source locally."
            )
            assert r["research_type"] in intent and r["human_scope"] in scope, (
                "Baseline annotation invariant failed; inspect the private source locally."
            )
            for k in ["intent_evidence", "scope_evidence"]:
                assert r[k] and r[k] in s["abstract"], (
                    "Baseline annotation invariant failed; inspect the private source locally."
                )
            result[r["blind_id"]] = r
    return result


F = DATA_DIR / "contemporaneous"
L = F / "labels"
a = read_labels("baseline_A_*.json", "baseline")
q = read_labels("baseline_QC_*.json", "baseline_QC")
t = read_labels("baseline_targeted_[0-9]*.json", "baseline_targeted")
assert len(a) == 1527 and len(q) == 374 and (len(t) == 452), (
    "Baseline annotation invariant failed; inspect the private source locally."
)
assert not set(q) & set(t), "Baseline annotation invariant failed; inspect the private source locally."
pairs = dict(q, **t)
adjudications = {}
for p in [L / "baseline_adjudicated.json"] + sorted(L.glob("baseline_targeted_adjudicated_[0-9]*.json")):
    for r in json.loads(p.read_text()):
        assert r["blind_id"] not in adjudications, (
            "Baseline annotation invariant failed; inspect the private source locally."
        )
        adjudications[r["blind_id"]] = r
source = {r["blind_id"]: r for p in (F / "packets").glob("baseline_[0-9]*.json") for r in json.loads(p.read_text())}


def validate(r):
    assert r["research_type"] in ["own_trial_planned", "mentor_led_trial_explicit", "other_research", "unclear"] and r[
        "human_scope"
    ] in ["applied", "BESH_only", "mixed_applied_BESH", "no_human_intervention", "unclear"], (
        "Baseline annotation invariant failed; inspect the private source locally."
    )
    assert r["adjudication_reason"] and r["reviewer_id"] and r["rationale"], (
        "Baseline annotation invariant failed; inspect the private source locally."
    )
    for k in ["intent_evidence", "scope_evidence"]:
        assert r[k] and r[k] in source[r["blind_id"]]["abstract"], (
            "Baseline annotation invariant failed; inspect the private source locally."
        )


for r in adjudications.values():
    validate(r)
changes = {r["blind_id"]: r for r in json.loads((L / "baseline_BESH_rechecked.json").read_text())}
assert len(changes) == 46, "Baseline annotation invariant failed; inspect the private source locally."
for r in changes.values():
    validate(r)
final = []
disagreements = set()
for i, r in a.items():
    reviewers = [r["reviewer_id"]]
    status = "single_review"
    label = r
    if i in pairs:
        b = pairs[i]
        assert b["reviewer_id"] not in reviewers, (
            "Baseline annotation invariant failed; inspect the private source locally."
        )
        reviewers.append(b["reviewer_id"])
        status = "dual_agreement"
        if any(r[k] != b[k] for k in ["research_type", "human_scope"]):
            disagreements.add(i)
            assert i in adjudications, "Baseline annotation invariant failed; inspect the private source locally."
            label = adjudications[i]
            assert label["reviewer_id"] not in reviewers, (
                "Baseline annotation invariant failed; inspect the private source locally."
            )
            reviewers.append(label["reviewer_id"])
            status = "adjudicated"
    if i in changes:
        assert i in pairs and i not in adjudications, (
            "Baseline annotation invariant failed; inspect the private source locally."
        )
        label = changes[i]
        assert label["reviewer_id"] not in reviewers, (
            "Baseline annotation invariant failed; inspect the private source locally."
        )
        reviewers.append(label["reviewer_id"])
        status = "systematic_scope_recheck"
    final.append(dict(label, reviewers=reviewers, review_status=status, label_kind="model_reference"))
assert set(adjudications) == disagreements, "Baseline annotation invariant failed; inspect the private source locally."
assert {r["blind_id"] for r in final} == set(a), (
    "Baseline annotation invariant failed; inspect the private source locally."
)
dump(F / "baseline_labels_final.json", sorted(final, key=lambda r: r["blind_id"]))
summary = {
    "n": len(final),
    "independent_double_review": len(pairs),
    "adjudicated_disagreements": len(disagreements),
    "agreed_BESH_mixed_reassessed": len(changes),
    "research_type": dict(Counter(r["research_type"] for r in final)),
    "human_scope": dict(Counter(r["human_scope"] for r in final)),
    "review_status": dict(Counter(r["review_status"] for r in final)),
}
dump(F / "baseline_final_summary.json", summary)
print("BASELINE FINAL", json.dumps(summary))
key = json.loads((F / "cohort_key_private.json").read_text())
base = {r["blind_id"]: r for r in final}
funding = json.loads((DATA_DIR / "cohort/funding_raw.json").read_text())
by = {r["pi_id"]: r for r in key}
funded = {r["blind_id"]: set() for r in key}
for award in funding:
    assert award["activity_code"] in ("R01", "R34", "U01")
    assert award["project_num_split"]["appl_type_code"] == "1"
    for pi in award["principal_investigators"]:
        person = by.get(pi["profile_id"])
        if person and person["start_date"] <= award["project_start_date"][:10] <= person["end_5y"]:
            funded[person["blind_id"]].add(award["activity_code"])
rows = []
for k in key:
    b = base[k["blind_id"]]
    row = {name: k[name] for name in ("blind_id", "mechanism", "group", "year", "ic")}
    row.update(
        eligible_main=int(b["human_scope"] != "BESH_only"),
        eligible_no_mixed=int(b["human_scope"] not in ("BESH_only", "mixed_applied_BESH")),
        research_type=b["research_type"],
        human_scope=b["human_scope"],
    )
    row.update({code: int(code in funded[k["blind_id"]]) for code in ("R01", "R34", "U01")})
    row["any_funding"] = int(bool(funded[k["blind_id"]]))
    rows.append(row)
table(F / "person_analysis.csv", rows)
print("baseline eligible:", sum(r["eligible_main"] for r in rows), "of", len(rows))
