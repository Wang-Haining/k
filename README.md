# NIH K trial pathways

Code, pseudonymized awardee data, and aggregate results for a study of trial leadership among NIH K08 and K23
career development awardees before and after the 2018 clinical trial pathways.

| Directory | Contents |
|---|---|
| `construct/` | Cohorts from NIH RePORTER, ClinicalTrials.gov retrieval, archived registry snapshots, protocol evidence, and model input packets |
| `measure/` | Prompts, JSON schemas, inference client, and a SLURM template |
| `outcomes/` | Awardee-level outcomes from model labels and rule fields |
| `analysis/` | Estimates reported in the paper |
| `validation/` | Rater codebook, validation sampling, scoring, and human-corrected estimates |
| `figures/` | Figures 1–4 and S1–S12 Tables |
| `data/public/` | Pseudonymized awardee-level analysis tables and aggregate disclosure checks |
| `results/` | Aggregate results used in the paper ([data dictionary](results/README.md)) |

## Data

`data/public/` contains 3,387 historical and 1,527 contemporaneous awardee rows
(the contemporaneous cohort is a subset of the historical comparison). These
analysis tables are derived from public NIH RePORTER and ClinicalTrials.gov
records and include sampled human reference states. IDs are **pseudonymous, not
anonymous**: linkage to public career records remains possible. Names, NIH profile
IDs, institution identifiers and names, abstracts, NCT identifiers, and
exact dates are excluded. No institution codes, institution-derived columns,
or linkage map are released.

The public tables reproduce point estimates for the historical adjusted DIDs
and joint contrasts, legacy and cohort-trend sensitivities, contemporaneous risk
differences, independent funding, and awardee-level registry-panel, reporting,
and seven-year analyses. Institution-clustered intervals require unreleased
cluster identifiers, available to editors and reviewers in confidence with the
rest of the confidential package. Institution-capacity contrasts and
human-corrected bootstrap-mean estimates also require that package.
[data/README.md](data/README.md) documents columns and
small cells; [results/README.md](results/README.md) lists exact reproduction
coverage and analyses requiring the confidential reviewer package or source
reconstruction. Linked source records are available from the corresponding
author for research use on reasonable request.

## Reproduce

Requirements: Python 3.11 or later, base R, and Arial for figures. The results were
verified with Python 3.12.13 and R 4.6.0.

```sh
python -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
make figures                                      # figures and S1 tables from results/
make public                                       # public awardee data -> results/public/; verify against results/
DATA_DIR=/path/to/inputs make analysis validation # results/ from the analytic files
```

Figure outputs are written to `figures/output/`. `make public` needs no private
data or network access: it expands `data/public/` into temporary input files,
runs the existing models with institution bootstraps skipped, and checks every
public point estimate and supporting count exactly against the shipped values.
Its outputs in `results/public/` are ignored by Git. Shipped
results are not overwritten. Seeded sampling and bootstrap draws depend on input
order in private reproduction; seeds are set in `config.py`. Person pseudonyms
preserve original sort order, and source row order is retained.

Construction requires network access, the frozen
[AACT 2022](https://zenodo.org/records/10091147) and
[CTTI 2024](https://zenodo.org/records/13984069) snapshots, and the curated
manifests described in `data/README.md`. Running it against live sources yields a
new snapshot. Protocol OCR also requires Poppler and Tesseract.

## Measurement

Trial intent and trial leadership were classified by `Qwen/Qwen3.8-27B-FP8`
(temperature 0, 1,024 output tokens, schema-constrained JSON, case-derived seeds)
with the prompts in `measure/prompts/`. Scientific lineage was rated by GPT-5.6 Sol
with `measure/prompts/lineage.md`. Model weights and container digests are not
pinned, so re-running inference produces a new measurement.

Two raters independently followed `validation/codebook.md` on a stratified random
sample of 280 awardee dossiers and on separate intent, K/new boundary, and lineage
samples. Human-corrected estimates impute outcome states within sampling cells
inside the institution bootstrap.

## Checks

```sh
Rscript -e 'install.packages("lintr", repos = "https://cloud.r-project.org")'
make check   # Ruff, lintr, ShellCheck, and figure rendering
```

## License

MIT. See [LICENSE](LICENSE).
