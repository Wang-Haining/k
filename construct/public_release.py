"""Build the allowlisted, pseudonymous awardee release; never export a linkage key."""

import csv
import re
from collections import Counter, defaultdict

from config import DATA_DIR, ROOT

BASE = "blind_id mechanism group year ic"
HISTORICAL = BASE + " period post intent primary secondary primary_fdaaa primary_4y preK_PI R01 R34"
CONTEMPORANEOUS = BASE + " eligible_main eligible_no_mixed research_type human_scope R01 R34 U01 any_funding"
EXTENDED = (
    "blind_id ktrial_direct ktrial_direct_fdaaa informative_strict new_trial_due new_trial_due_with_results "
    "primary_nihdef primary_late nonpi_multisite ktrial_timely primary_timely new_trial_due_results12 "
    "nih_new_trial nih_new_trial_own_grant ktrial_any_start ktrial_grant_linked ktrial_judged_unlinked "
    "R01eq_5y R01eq_7y R01eq_or_trialgrant_5y R01nih_5y R01nih_7y R01nih_R35_5y "
    "R01nih_or_trialgrant_5y followup_7y_complete"
)
VARIANTS = (
    "blind_id secondary_main primary_main primary_window_4y primary_excl_basic_science "
    "primary_excl_withdrawn_zero primary_excl_start_conflict primary_registry_roles_only "
    "primary_current_record_only preK_PI unresolved"
)
PANEL_CATS = ["a_pi_from_registration", "b_link_added_later_or_never", "c_responsibility_shift", "d_insufficient"]
PANEL_FLAGS = [
    "v0_awardee_pi",
    "other_pi_v0",
    "awardee_added_later",
    "klink_v0",
    "klink_added_later",
    "started",
    "completed",
    "completed_within_5y",
    "stopped",
    "results",
    "published",
    "awardee_first_last",
]
PANEL = ["has_k_trial", *PANEL_CATS, *PANEL_FLAGS]
# The same allowlist expands the two tables back into the existing scripts' inputs.
SOURCES = {
    "historical/person_analysis.csv": HISTORICAL,
    "contemporaneous/person_analysis.csv": CONTEMPORANEOUS,
    "derived/historical_extended.csv": EXTENDED + " besh_only_classifier",
    "derived/contemporaneous_extended.csv": EXTENDED,
    "instrument/analysis/person_variants.csv": VARIANTS,
    "derived/historical_prior_trials.csv": "blind_id preK_PI_nonK",
    "derived/contemporaneous_prior_trials.csv": "blind_id preK_PI_nonK",
    "derived/historical_reporting.csv": "blind_id stratum ktrial_due ktrial_due_results ktrial_due_results12",
    "derived/historical_seven_year.csv": "blind_id new_trial_7y new_trial_years_5_7_only new_trial_7y_timely",
    "derived/revision_person.csv": (
        "blind_id k_id_field k_text k_none k_no_text new_no_text k_excl_covid new_excl_covid "
        "new_5y_registered new_7y_registered"
    ),
    "validation/reference_dossier_private.csv": (
        "blind_id stratum intent instrument_cell instrument_state ref_primary ref_swap ref_rater_a ref_rater_b"
    ),
    "validation/reference_intent_private.csv": "blind_id stratum call human_intent",
}
SAMPLED = {
    "derived/historical_seven_year.csv": "seven_year_sample",
    "validation/reference_dossier_private.csv": "dossier_sample",
    "validation/reference_intent_private.csv": "intent_sample",
}


def read(path):
    with path.open() as handle:
        rows = list(csv.DictReader(handle))
    assert rows, f"empty input: {path.name}"
    return rows


def write(path, rows):
    assert rows, f"no output rows: {path.name}"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    print(f"{path.name}: {len(rows)} rows, {len(rows[0])} columns")


def keyed(rows):
    out = {r["blind_id"]: r for r in rows}
    assert len(out) == len(rows), f"duplicate awardee keys: {len(rows) - len(out)}"
    return out


def cohort(path):
    return "contemporaneous" if "contemporaneous" in path or path.startswith("instrument/") else "historical"


def build():
    tables = {c: keyed(read(DATA_DIR / c / "person_analysis.csv")) for c in ("historical", "contemporaneous")}
    expected = {"historical": 3387, "contemporaneous": 1527}
    out = {c: {b: {} for b in rows} for c, rows in tables.items()}
    for path, columns in SOURCES.items():
        source = keyed(read(DATA_DIR / path))
        target = out[cohort(path)]
        assert source.keys() <= target.keys(), f"unmatched awardees: {path}"
        if path not in SAMPLED:
            assert source.keys() == target.keys(), f"incomplete input: {path}"
        columns = columns.split()
        assert set(columns) <= source[next(iter(source))].keys(), f"missing columns: {path}"
        for b, row in target.items():
            if path in SAMPLED:
                row[SAMPLED[path]] = str(int(b in source))
            for k in columns:
                value = source[b][k] if b in source else ""
                if k in row:
                    assert b not in source or row[k] == value, f"conflicting column {k}: {path}"
                else:
                    row[k] = value
    starts = keyed(read(DATA_DIR / "historical/persons.csv"))
    assert starts.keys() == out["historical"].keys(), "start roster mismatch"
    records = defaultdict(list)
    for r in read(DATA_DIR / "derived/ktrial_panel_records_private.csv"):
        if r["window"] == "inside":
            records[r["blind_id"]].append(r)
    for b, row in out["historical"].items():
        state = f"k{row['ktrial_direct']}p{row['primary']}"
        cell = "new_trial" if row["primary"] == "1" else "ktrial_only" if row["ktrial_direct"] == "1" else "none"
        assert row["instrument_state"] in ("", state), "instrument joint-state mismatch"
        assert row["instrument_cell"] in ("", cell), "instrument sampling-cell mismatch"
        row["instrument_state"], row["instrument_cell"] = state, cell
        date = starts[b]["start_date"]
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", date), "invalid start-date format"
        row["start_ge_2018"] = str(int(date >= "2018-01-01"))
        row["start_ge_2017_09"] = str(int(date >= "2017-09-01"))
        row["panel_sample"] = str(
            int(row["mechanism"] == "K23" and row["intent"] == "1" and row["besh_only_classifier"] == "0")
        )
        xs = records[b]
        flags = {"has_k_trial": int(bool(xs))}
        flags.update({k: int(any(r["cat"] == k for r in xs)) for k in PANEL_CATS})
        flags.update({k: int(any(r[k] == "1" for r in xs)) for k in PANEL_FLAGS})
        row.update({k: str(flags[k]) if row["panel_sample"] == "1" else "" for k in PANEL})
    variants = keyed(read(DATA_DIR / "instrument/analysis/person_variants.csv"))
    for b, row in out["contemporaneous"].items():
        row["intent"] = out["historical"][b]["intent"]
        for kind in ("primary", "secondary"):
            t = variants[b][f"t_first_{kind}"]
            for year in range(1, 6):
                row[f"{kind}_by_{year}y"] = str(int(t not in ("", "NA", "nan") and float(t) <= year))
    person_ids = {b: f"P{i:05d}" for i, b in enumerate(sorted(out["historical"]), 1)}
    # Person pseudonyms retain sort order; no linkage map is written.
    audit = []
    public = ROOT / "data/public"
    for c, rows in out.items():
        assert len(rows) == expected[c], f"{c}: expected {expected[c]} rows, got {len(rows)}"
        reduced = Counter(tuple(r[k] for k in ("mechanism", "year", "ic")) for r in rows.values())
        audit.append(
            {
                "cohort": c,
                "n": len(rows),
                "singleton_without_cluster": sum(n == 1 for n in reduced.values()),
            }
        )
        for b, r in rows.items():
            r["blind_id"] = person_ids[b]
            for k, value in r.items():
                assert not re.search(r"NCT\d{8}|\d{4}-\d{2}-\d{2}", value), f"forbidden value in {c}.{k}"
                if k not in {
                    "blind_id",
                    "mechanism",
                    "group",
                    "ic",
                    "period",
                    "stratum",
                    "research_type",
                    "human_scope",
                    "instrument_cell",
                    "instrument_state",
                    "ref_primary",
                    "ref_swap",
                    "ref_rater_a",
                    "ref_rater_b",
                }:
                    assert value == "" or value.isdigit(), f"unexpected nonnumeric value in {c}.{k}"
                    if k != "year":
                        assert value in ("", "0", "1"), f"unexpected nonbinary value in {c}.{k}"
        write(public / f"{c}_awardees.csv", list(rows.values()))
        print(f"{c}: singleton without institution={audit[-1]['singleton_without_cluster']}")
    write(public / "disclosure_check.csv", audit)
    (public / "reporting_bootstrap_clusters.csv").unlink(missing_ok=True)
    print(f"release: {len(person_ids)} distinct awardees; no institution columns or linkage map exported")


def adapt(public, target):
    """Expand only public fields into temporary inputs for the existing analysis scripts."""
    tables = {c: read(public / f"{c}_awardees.csv") for c in ("historical", "contemporaneous")}
    for path, columns in SOURCES.items():
        rows = tables[cohort(path)]
        if path in SAMPLED:
            rows = [r for r in rows if r[SAMPLED[path]] == "1"]
        if path == "instrument/analysis/person_variants.csv":
            columns += " " + " ".join(f"{kind}_by_{y}y" for kind in ("primary", "secondary") for y in range(1, 6))
        write(target / path, [{k: r[k] for k in columns.split()} for r in rows])
    write(
        target / "historical/persons.csv",
        [{k: r[k] for k in ("blind_id", "start_ge_2018", "start_ge_2017_09")} for r in tables["historical"]],
    )
    write(
        target / "derived/ktrial_panel_awardees.csv",
        [{k: r[k] for k in ["blind_id", *PANEL]} for r in tables["historical"] if r["panel_sample"] == "1"],
    )
    eligible = [r for r in tables["historical"] if r["mechanism"] == "K23" and r["besh_only_classifier"] == "0"]
    cells = Counter((r["stratum"], r["intent"], r["instrument_cell"]) for r in eligible)
    write(
        target / "validation/key_private.csv",
        [
            {
                "blind_id": r["blind_id"],
                "module": "dossier",
                "stratum": r["stratum"],
                "intent": r["intent"],
                "instrument_state": r["instrument_cell"],
                "cell_population": cells[r["stratum"], r["intent"], r["instrument_cell"]],
            }
            for r in eligible
            if r["dossier_sample"] == "1"
        ],
    )
    print("public adapter: awardee inputs only; no trial linkage or exact dates")


if __name__ == "__main__":
    build()
