"""Export cell populations and sample sizes from the pooled dossier key."""

import csv
from collections import defaultdict

from config import DATA_DIR, RESULTS_DIR


def main():
    cells = defaultdict(list)
    with (DATA_DIR / "validation/key_private.csv").open() as handle:
        for row in csv.DictReader(handle):
            if row["module"] == "dossier":
                cells[row["stratum"], row["intent"], row["instrument_state"]].append(row)
    rows = []
    for (stratum, intent, state), members in sorted(cells.items()):
        populations = {int(r["cell_population"]) for r in members}
        assert len(populations) == 1, f"expected one population, got {len(populations)}"
        assert len({r["blind_id"] for r in members}) == len(members), "duplicate sampled awardee"
        rows.append(
            {
                "stratum": stratum,
                "intent": intent,
                "instrument_state": state,
                "cell_population": populations.pop(),
                "sampled": len(members),
            }
        )
    assert len(rows) == 18 and sum(r["sampled"] for r in rows) == 280
    assert sum(r["cell_population"] for r in rows) == 1847
    with (RESULTS_DIR / "validation/validation_design.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    print("validation design: 18 cells / 280 sampled / 1847 population")


if __name__ == "__main__":
    main()
