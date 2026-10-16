"""Locations of private analytic inputs and public aggregate results."""

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA_DIR = Path(os.environ.get("DATA_DIR", ROOT / "data")).resolve()
RESULTS_DIR = Path(os.environ.get("RESULTS_DIR", ROOT / "results")).resolve()

ANALYSIS_SEED = 2026
DID_CORRECTION_SEED = 2039
LINEAGE_CORRECTION_SEED = 2041
COHORT_SEED = 20260927
DOSSIER_SAMPLE_SEED = "2026-human-v3"
DOSSIER_ADDITIONAL_SEED = "2026-human-v3-expand"
DOSSIER_ASSIGNMENT_SEED = "2026-human-v3-assign"
