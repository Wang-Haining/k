PYTHON ?= python3
RSCRIPT ?= Rscript
export DATA_DIR := $(shell $(PYTHON) -c 'from config import DATA_DIR; print(DATA_DIR)')
export RESULTS_DIR := $(shell $(PYTHON) -c 'from config import RESULTS_DIR; print(RESULTS_DIR)')

export ANALYSIS_SEED := $(shell $(PYTHON) -c 'from config import ANALYSIS_SEED; print(ANALYSIS_SEED)')
export DID_CORRECTION_SEED := $(shell $(PYTHON) -c 'from config import DID_CORRECTION_SEED; print(DID_CORRECTION_SEED)')

.PHONY: figures analysis validation public lint check
figures:
	$(PYTHON) -m figures.main
	$(PYTHON) -m figures.supplement

public:
	$(PYTHON) -m analysis.public

analysis:
	@test -f "$(DATA_DIR)/contemporaneous/person_analysis.csv" || (echo "DATA_DIR must contain the analytic inputs"; exit 1)
	mkdir -p "$(RESULTS_DIR)/validation"
	$(RSCRIPT) analysis/contemporaneous.R
	$(PYTHON) -m analysis.trial_quality
	$(RSCRIPT) analysis/hazards.R
	$(RSCRIPT) analysis/historical.R
	$(RSCRIPT) analysis/extended.R
	$(RSCRIPT) analysis/registration_reporting.R
	$(PYTHON) -m outcomes.prior_trial_audit
	$(RSCRIPT) analysis/nih_funding.R
	$(PYTHON) -m analysis.ktrial_descriptives
	$(RSCRIPT) analysis/composition_boundary.R
	$(RSCRIPT) analysis/joint_did_reporting.R
	$(PYTHON) -m analysis.leadership_panel
	$(PYTHON) -m analysis.lineage "$(DATA_DIR)/ratings/lineage_labels.csv"
	$(RSCRIPT) analysis/prior_capacity.R
	$(RSCRIPT) analysis/seven_year.R
	$(PYTHON) -m analysis.contemporaneous_intent
	$(PYTHON) -m analysis.observed_cell_means
	$(PYTHON) -m outcomes.revision
	$(RSCRIPT) analysis/revision.R

validation:
	$(PYTHON) -m validation.score score
	$(PYTHON) -m validation.pool
	$(PYTHON) -m validation.design
	$(PYTHON) -m validation.reference
	$(RSCRIPT) validation/correct_did.R
	$(PYTHON) -m validation.correct_lineage

lint:
	ruff check .
	ruff format --check .
	$(RSCRIPT) -e 'x <- lintr::lint_dir("."); print(x); if (length(x)) quit(status=1)'
	shellcheck measure/infer.sbatch

check: lint figures
