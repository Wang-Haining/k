"""Run shared models without institution bootstraps; verify shipped point estimates."""

import csv
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from config import ANALYSIS_SEED, DID_CORRECTION_SEED, ROOT
from construct.public_release import adapt

R_SCRIPTS = (
    "analysis/contemporaneous.R",
    "analysis/historical.R",
    "analysis/extended.R",
    "analysis/registration_reporting.R",
    "analysis/nih_funding.R",
    "analysis/joint_did_reporting.R",
    "analysis/seven_year.R",
    "analysis/revision.R",
)


def main():
    public = ROOT / "data/public"
    with tempfile.TemporaryDirectory(prefix="k-public-") as folder:
        inputs = Path(folder)
        output = inputs / "results"
        adapt(public, inputs)
        env = dict(
            os.environ,
            DATA_DIR=str(inputs),
            RESULTS_DIR=str(output),
            PUBLIC="1",
            ANALYSIS_SEED=str(ANALYSIS_SEED),
            DID_CORRECTION_SEED=str(DID_CORRECTION_SEED),
        )
        # No aggregate reference is read by the models: revision's funding/legacy checks
        # use the newly computed results. Shipped CSVs are read only for verification.
        output.mkdir(parents=True, exist_ok=True)
        (output / "follow_up").mkdir(exist_ok=True)
        (output / "validation").mkdir(exist_ok=True)
        for script in R_SCRIPTS:
            print(f"public: {script}", flush=True)
            subprocess.run([os.environ.get("RSCRIPT", "Rscript"), script], cwd=ROOT, env=env, check=True)
        for module in (
            "analysis.leadership_panel",
            "analysis.contemporaneous_intent",
            "analysis.observed_cell_means",
            "analysis.ktrial_descriptives",
            "validation.design",
        ):
            subprocess.run([sys.executable, "-m", module], cwd=ROOT, env=env, check=True)
        # Publish only point estimates and supporting counts; no bootstrap output.
        excluded = {
            "lo",
            "hi",
            "se",
            "mde80",
            "na_reps",
            "reps",
            "n_institutions",
            "CI_low",
            "CI_high",
            "fisher_p",
            "interval_method",
        }
        total = files = 0
        for path in sorted(output.rglob("*.csv")):
            relative = path.relative_to(output)
            shipped = ROOT / "results" / relative
            with path.open() as handle:
                reader = csv.DictReader(handle)
                columns = [k for k in reader.fieldnames if k not in excluded]
                rows = [{k: r[k] for k in columns} for r in reader]
            with shipped.open() as handle:
                reader = csv.DictReader(handle)
                assert columns == [k for k in reader.fieldnames if k not in excluded], f"schema mismatch: {relative}"
                expected = [{k: r[k] for k in columns} for r in reader]
            assert rows and rows == expected, f"public point-estimate mismatch: {relative}"
            with path.open("w", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=columns, lineterminator="\n")
                writer.writeheader()
                writer.writerows(rows)
            files += 1
            total += len(rows)
            print(f"verified {relative}: {len(rows)} exact point-estimate/supporting rows")
        assert files == 27 and total == 426, f"incomplete public results: {files} files, {total} rows"
        destination = ROOT / "results/public"
        if destination.exists():
            shutil.rmtree(destination)
        shutil.copytree(output, destination)
        print(f"public verification: {files} files; {total} exact point-estimate/supporting rows; no intervals")


if __name__ == "__main__":
    main()
