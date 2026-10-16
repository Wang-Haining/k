"""Export unadjusted new-trial DIDs from eligible historical awardees."""

import csv
from collections import defaultdict

from config import DATA_DIR, RESULTS_DIR


def main():
    with (DATA_DIR / "historical/person_analysis.csv").open() as handle:
        people = list(csv.DictReader(handle))
    with (DATA_DIR / "derived/historical_extended.csv").open() as handle:
        excluded = {r["blind_id"] for r in csv.DictReader(handle) if r["besh_only_classifier"] == "1"}
    rows = []
    for mechanism in ("K23", "K08"):
        cells = defaultdict(list)
        for person in people:
            if person["mechanism"] == mechanism and person["blind_id"] not in excluded:
                cells[person["post"], person["intent"]].append(int(person["primary"]))
        assert len(cells) == 4, f"expected 4 cells, got {len(cells)}"
        means = {key: sum(values) / len(values) for key, values in cells.items()}
        did = 100 * (means["1", "1"] - means["1", "0"] - (means["0", "1"] - means["0", "0"]))
        rows.append({"mechanism": mechanism, "outcome": "primary", "observed": round(did, 1)})
    with (RESULTS_DIR / "historical/observed_cell_means.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    print("observed cell means:", len(rows), "contrasts", [r["observed"] for r in rows])


if __name__ == "__main__":
    main()
