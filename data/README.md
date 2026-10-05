# Analytic inputs

## Public awardee release

`public/historical_awardees.csv` has one row for each of 3,387 awardees;
`public/contemporaneous_awardees.csv` has 1,527 rows, all also present in the
historical comparison. The tables derive from public NIH RePORTER and
ClinicalTrials.gov records and frozen instrument and human classifications.
They are **pseudonymized, not anonymous**. Do not interpret the absence of direct
identifiers as protection against linkage to public career records.

`blind_id` is a new zero-padded person code, consistent across tables. Its sort
order matches the original analytic key; original row order is also retained.
Names, NIH profile IDs, institution names and identifiers (including `org_id`),
all institution-derived columns, abstracts, trial IDs/linkage, and exact dates are
excluded by an explicit column allowlist in `construct/public_release.py`.
No institution cluster counts or linkage map are released.

The small-cell check groups mechanism × fiscal year × IC, without institution.
It finds **34 singleton awardees among 3,387 historical rows** and **15 among
1,527 contemporaneous rows**. `public/disclosure_check.csv` records these counts.
This is not a claim of k-anonymity. Fiscal year, mechanism, and IC (the NIH
funding institute, not the awardee institution) are retained because the models
use them.

The public tables reproduce point estimates. Institution-clustered intervals use
cluster identifiers that are not released and are available to editors and
reviewers in confidence with the rest of the confidential package. That package
is also required for institution-capacity contrasts and human-corrected point
estimates defined as institution-bootstrap draw means.

Public columns follow the existing vocabulary and definitions below:

- Both tables: `blind_id`, `mechanism`, `group`, `year`, `ic`, instrument
  `intent`, `preK_PI`, `preK_PI_nonK`, `R01`, `R34`, and the allowlisted extended
  outcome columns. These include K-trial/new-trial timing, reporting and funding
  indicators, complete-seven-year follow-up, and the R01-equivalent definitions.
- Historical: `period`, `post`, `primary`, `secondary`, `primary_fdaaa`,
  `primary_4y`, `besh_only_classifier`, `stratum`, `ktrial_due`,
  `ktrial_due_results`, `ktrial_due_results12`; seven-year `new_trial_7y`,
  `new_trial_years_5_7_only`, `new_trial_7y_timely`; and revision `k_id_field`,
  `k_text`, `k_none`, `k_no_text`, `new_no_text`, `k_excl_covid`,
  `new_excl_covid`, `new_5y_registered`, `new_7y_registered`.
- Historical date replacements: `start_ge_2018` and `start_ge_2017_09` are the
  existing calendar-start restrictions (at least 2018-01-01 and 2017-09-01).
  They preserve eligibility without disclosing an exact start date.
- Human validation: `dossier_sample`, `instrument_cell` (none, K-only, or new),
  `instrument_state` (`k0p0`, `k0p1`, `k1p0`, `k1p1`), `ref_primary`, `ref_swap`,
  `ref_rater_a`, `ref_rater_b`; `intent_sample`, `call`, `human_intent`.
  Sampling cells are stratum × instrument intent × `instrument_cell`; correction
  refines them by `instrument_state`. Human reference variants have exactly the
  definitions in `results/README.md`. A blank human state is unresolved or
  unsampled, distinguished by the sample flag. `seven_year_sample` similarly
  identifies the complete-follow-up subset; outside it the seven-year endpoints
  are blank, not zero.
- Historical panel: `panel_sample` identifies the 721 eligible K23 instrument-intent
  awardees. `has_k_trial`, the four category flags
  `a_pi_from_registration`, `b_link_added_later_or_never`,
  `c_responsibility_shift`, `d_insufficient`, and `v0_awardee_pi`, `other_pi_v0`,
  `awardee_added_later`, `klink_v0`, `klink_added_later`, `started`, `completed`,
  `completed_within_5y`, `stopped`, `results`, `published`, `awardee_first_last`
  indicate any qualifying trial with that feature. Categories can overlap
  across one awardee's trials. Values outside the panel sample are blank.
- Contemporaneous: `eligible_main`, `eligible_no_mixed`, `research_type`,
  `human_scope`, `U01`, `any_funding`, `primary_main`, `secondary_main`,
  the six `primary_` sensitivity variants in the input dictionary below, and
  `unresolved`. `primary_by_1y` through `primary_by_5y` and `secondary_by_1y`
  through `secondary_by_5y` replace exact event times with the annual indicators
  actually used by the cumulative analysis. Unresolved awardees remain excluded
  by the existing code.

Only required columns from the private files below are released; their CSV
headers and the builder's `SOURCES` allowlist are the exact schema. Binary
indicators use 0/1. The two awardee tables contain 88 and 59 columns, respectively.
`make public` skips institution bootstraps and writes point estimates and
supporting counts only; no institution-derived file is needed.

Run `make public` for analysis and aggregate verification. To rebuild the release
from the frozen private inputs after `make analysis validation`, use:

```sh
DATA_DIR=/path/to/private/inputs python -m construct.public_release
```

The builder prints only counts, exports no mapping, and leaves private inputs
unchanged. Preserve the public file order for reproducibility.

## Private construction and validation inputs

Supply the following paths under `DATA_DIR`; linked source records belong outside
the public repository. Do not sort or deduplicate supplied inputs. CSV headers
are case-sensitive; absent outcomes use the supplied empty/NA values, never
invented zeros. JSON and workbook row order must also be retained.

`blind_id`, `case_id`, `item`, and `trial` are linkable private keys. `primary` means a distinct new trial, `secondary` any qualifying trial, and `ktrial_direct` the K trial within five years. Binary endpoints use 0/1; pair flags use True/False. `intent` denotes own-trial planning; `post` indicates the new announcement regime. `ic`, `year` and `org_id` support adjustment and institution resampling. `pre_legacy` denotes earlier announcements with award starts in 2018–2019.

## `contemporaneous/person_analysis.csv`

Baseline eligibility, mechanism, announcement group, fiscal year, institute, baseline research classification and funding indicators. Only analysis columns are used.

Columns: `blind_id`, `mechanism`, `group`, `year`, `ic`, `eligible_main`, `eligible_no_mixed`, `research_type`, `human_scope`, `R01`, `R34`, `U01`, `any_funding`. Other columns in frozen files are unused.

## `contemporaneous/cohort_key_private.json`

Ordered cohort records: blind_id, pi_id, first_name, last_name, start_date, end_5y, org_id, institution; panel date windows and outcome assembly.

## `instrument/analysis/person_variants.csv`

Per-awardee trial-leadership sensitivities, time to first trial, prior leadership, unresolved timing and institution.

Columns: `blind_id`, `org_id`, `institution`, `secondary_main`, `primary_main`, `secondary_window_4y`, `primary_window_4y`, `secondary_excl_basic_science`, `primary_excl_basic_science`, `secondary_excl_withdrawn_zero`, `primary_excl_withdrawn_zero`, `secondary_excl_start_conflict`, `primary_excl_start_conflict`, `secondary_registry_roles_only`, `primary_registry_roles_only`, `secondary_current_record_only`, `primary_current_record_only`, `t_first_primary`, `t_first_secondary`, `n_primary_trials`, `preK_PI`, `unresolved`.

## `instrument/instrument_pair_outcomes.csv`

Person–trial instrument states and rule fields; used to aggregate trial characteristics and prior-trial audits.

Columns: `case_id`, `blind_id`, `nct_id`, `start_date`, `window`, `k_link`, `identity`, `name_guard`, `role`, `role_source`, `scope`, `k_relationship`, `secondary_pair`, `primary_pair`, `preK_pair`, `timing_unresolved_pair`, `flag_withdrawn_zero`, `flag_start_conflict`, `primary_purpose`.

## `instrument/trial_features.json`

Object keyed by NCT identifier: registry design, enrollment, site count, phases, sponsor/funder classes, NIH identifiers, start/submission/completion/results dates, and status.

## `historical/person_analysis.csv`

Both-period cohort, trial intent, five-year leadership outcomes, prior leadership, funding and adjustment covariates.

Columns: `blind_id`, `period`, `post`, `mechanism`, `nofo`, `group`, `year`, `ic`, `org_id`, `intent`, `intent_label`, `primary`, `secondary`, `primary_fdaaa`, `primary_4y`, `primary_excl_withdrawn`, `preK_PI`, `R01`, `R34`, `U01`, `any_funding`.

## `historical/persons.csv`

Start-date roster; only blind_id and start_date are needed by the regressions.

Columns: `blind_id`, `pi_id`, `period`, `mechanism`, `nofo`, `group`, `year`, `start_date`, `ic`, `org_id`, `first_name`, `last_name`.

## `historical/pairs.csv`

Candidate pair rule fields, including case_id, blind_id, nct_id, study_type, window, k_link and screening flags.

Columns: `case_id`, `blind_id`, `nct_id`, `study_type`, `primary_purpose`, `start_date`, `start_type`, `window`, `qwen_reviewed`, `k_link`, `fdaaa_like`, `flag_withdrawn_zero`.

## `historical/pair_outcomes.csv`

Frozen primary, secondary and pre-K pair outcomes.

Columns: `case_id`, `blind_id`, `secondary_pair`, `primary_pair`, `preK_pair`.

## `historical/cohort_key_private.json`

Earlier ordered cohort records with the same keys plus period; panel date windows and outcome assembly.

## `derived/contemporaneous_characteristics.csv`

Person-level trial characteristics and supporting funding outcomes.

Columns: `blind_id`, `first_primary_start`, `first_secondary_start`, `informative_new_trial`, `multisite_new_trial`, `completed_with_results`, `new_trial_completed_due`, `nih_funded_new_trial`, `industry_new_trial`, `k_trial_registered_as_PI`, `R01eq`, `R01eq_contact_PI`.

## `derived/historical_characteristics.csv`

Both-period person-level trial characteristics and first-event dates.

Columns: `blind_id`, `first_primary_start`, `first_secondary_start`, `informative_new_trial`, `multisite_new_trial`, `completed_with_results`, `new_trial_completed_due`, `nih_funded_new_trial`, `industry_new_trial`, `k_trial_registered_as_PI`, `R01eq`, `R01eq_contact_PI`.

## `derived/historical_person_years.csv`

Discrete-time risk panel: k is years since K start; cal_year is the midpoint calendar year; event marks first new-trial start.

Columns: `blind_id`, `k`, `cal_year`, `event`.

## `derived/contemporaneous_extended.csv`

K/new trial leadership, timing/reporting, NIH funding, prior awards and complete-follow-up indicators.

Columns: `blind_id`, `ktrial_direct`, `ktrial_direct_fdaaa`, `informative_strict`, `new_trial_due`, `new_trial_due_with_results`, `primary_nihdef`, `primary_late`, `nonpi_multisite`, `ktrial_timely`, `primary_timely`, `new_trial_due_results12`, `nih_new_trial`, `nih_new_trial_own_grant`, `ktrial_any_start`, `ktrial_grant_linked`, `ktrial_judged_unlinked`, `primary_judgment_only`, `primary_link_only`, `n_trials_led`, `two_plus_trials`, `prior_nih_pi_award`, `prior_research_grant`, `R01eq_5y`, `R01eq_7y`, `R01eq_or_trialgrant_5y`, `R01nih_5y`, `R01nih_7y`, `R01nih_R35_5y`, `R01nih_or_trialgrant_5y`, `followup_7y_complete`.

## `derived/historical_extended.csv`

The same supporting endpoints across periods, including besh_only_classifier for common historical eligibility.

Columns: `blind_id`, `ktrial_direct`, `ktrial_direct_fdaaa`, `informative_strict`, `new_trial_due`, `new_trial_due_with_results`, `primary_nihdef`, `primary_late`, `nonpi_multisite`, `ktrial_timely`, `primary_timely`, `new_trial_due_results12`, `nih_new_trial`, `nih_new_trial_own_grant`, `ktrial_any_start`, `ktrial_grant_linked`, `ktrial_judged_unlinked`, `primary_judgment_only`, `primary_link_only`, `n_trials_led`, `two_plus_trials`, `prior_nih_pi_award`, `prior_research_grant`, `R01eq_5y`, `R01eq_7y`, `R01eq_or_trialgrant_5y`, `R01nih_5y`, `R01nih_7y`, `R01nih_R35_5y`, `R01nih_or_trialgrant_5y`, `followup_7y_complete`, `besh_only_classifier`.

## `derived/contemporaneous_prior_trials.csv`

Prior trial leadership after excluding the K trial.

Columns: `blind_id`, `preK_PI_nonK`.

## `derived/historical_prior_trials.csv`

Prior non-K trial leadership across both periods.

Columns: `blind_id`, `preK_PI_nonK`.

## `derived/historical_reporting.csv`

Earlier-announcement and post-policy strata, completed K-trial reporting eligibility and results indicators.

Columns: `blind_id`, `stratum`, `ktrial_due`, `ktrial_due_results`, `ktrial_due_results12`.

## `derived/historical_seven_year.csv`

Complete-seven-year follow-up subset and extended leadership outcomes.

Columns: `blind_id`, `new_trial_7y`, `new_trial_years_5_7_only`, `new_trial_7y_timely`.

## `derived/ktrial_pairs.csv`

Qualifying K-trial roster; analysis identifies contemporaneous (main) or historical records.

Columns: `analysis`, `blind_id`, `nct_id`, `start_date`, `window`, `k_grant_linked`.

## `derived/ktrial_history.json`

Object keyed by NCT: `ev` contains ordered `[version, reserved, names, linked]` events; `rec` records recruitment/activity. See the precise version schema below.

## `derived/ktrial_pubmed.json`

Object keyed by NCT, listing indexed publications; first and last author objects contain fore and last names for the panel name guard.

## `derived/ktrial_panel_input_private.json`

Ordered rows with `i` (zero-based row number), `blind_id`, `nct`, `first`, `last`, `serial` (NIH institute plus six-digit award serial), and `window`. Start dates are joined from the K-trial roster.

## `ratings/lineage_sample_private.csv`

Private item-to-person/pair mapping and period/K-trial sampling cells for lineage.

Columns: `item`, `case_id`, `blind_id`, `period`, `has_ktrial`.

## `ratings/lineage_labels.csv`

Frozen scientific-lineage classifications: item, lineage and reason. Model categories are in `measure/prompts/lineage.md`; the separate human instrument is in `validation/codebook.md`.

Columns: `item`, `lineage`, `reason`.

## `validation/key_private.csv`

Pooled sampling key. dossier/dossier_trial/intent/boundary/lineage identify modules; instrument_label is JSON; cell_population gives inverse-sampling weights.

Columns: `module`, `item`, `blind_id`, `case_id`, `stratum`, `intent`, `instrument_state`, `cell_population`, `instrument_label`.

## `validation/initial_key.csv`

Initial double-rated sampling key, aligned to the adjudicated returned workbooks.

Columns: `module`, `item`, `blind_id`, `case_id`, `stratum`, `intent`, `instrument_state`, `cell_population`, `instrument_label`.

## `validation/assignment_private.csv`

Additional dossier assignment: set is single or overlap; raters and reference_rater use rater_a/rater_b.

Columns: `item`, `set`, `raters`, `reference_rater`.

## Human returns

`validation/returned/rating_rater_a.xlsx` and `rating_rater_b.xlsx` contain `dossier_awardees`, `dossier_trials`, `intent`, `boundary`, and `lineage`. Supplied fields are those created by `validation/sample.py`; categorical answer fields and their meanings are specified in the codebook. The shared keys are `item` and (for trial rows) `trial`. dossier also includes `search_done` and `missed_trials_found`.

`validation/returned/adjudication.xlsx` contains the `adjudication` sheet, with columns `module`, `item`, `field`, `rater_a`, `rater_b`, `final`. Every disagreement must have a resolved final answer.

`validation/additional_returns/rating_rater_a.xlsx` and `rating_rater_b.xlsx` contain each assigned additional dossier and trial, plus the retained initial answers. Only dossier sheets supply the pooled additional reference.

The validation target writes two private per-awardee exports:
- `validation/reference_dossier_private.csv`: blind_id, stratum, intent, instrument_cell,
  instrument_state, ref_primary, ref_swap, ref_rater_a, ref_rater_b. Joint states encode
  K and new-trial leadership; unresolved human states are empty.
- `validation/reference_intent_private.csv`: blind_id, stratum, call, human_intent.
  Unresolved human intent is empty.

The sensitivity analysis also requires `historical/packets.jsonl`,
`historical/seven_year_packets.jsonl` and `historical/seven_year_labels/labels/*.json`
listed below. It writes only private intermediates to `derived/revision_person.csv`
and `derived/revision_reporting.csv`; all released sensitivity tables are aggregates.

## Frozen instrument labels

`historical/intent_labels/*.json` contains one successful result per awardee; `label.research_type` and `label.human_intervention_scope` follow the intent schema. `historical/leadership_labels/*.json` contains successful person–trial labels following the leadership schema. Filenames are private identifiers. Each result includes `status`, `case_id`, `packet_sha256`, `prompt_sha256`, `model`, and `label`. New inference outputs also record `schema_sha256`; never mix measurement specifications.

## Additional inputs for sampling and outcome construction

These support construction and sampling. The sensitivity analysis additionally uses the historical and seven-year packets and labels listed here:

- `historical/intent_packets.jsonl`: case_id, K_title, K_abstract after announcement masking.
- `historical/packets.jsonl` and `reviewed_packets.jsonl`: ordered complete and screened registry-only person–trial packets. Each has case_id, packet_sha256, awardee, trial, historical_registry_snapshots, protocol_excerpts.
- `instrument/qwen/packets_all.jsonl` and `instrument/qwen/leadership_labels/*.json`: contemporaneous packets and frozen labels; `instrument/pair_screen.csv` supplies deterministic study_type, window, k_link, dates and flags.
- `ratings/krel_rater_sheet.csv` and `krel_sample_private.csv`: masked scientific K/new fields and a private item/case mapping with analysis, period and instrument_class.
- `ratings/lineage_rater_sheet.csv`: item, masked K_title/K_abstract, Ktrial_* and new_* scientific fields, with no timing/group information.
- `historical/seven_year_packets.jsonl` and `seven_year_labels/labels/*.json`: additional five-to-seven-year packets and their frozen labels.
- `cohort/funding_raw.json` and `historical/funding_raw.json`: saved RePORTER funding responses, containing activity_code, project_num_split.appl_type_code, project_start_date and principal_investigators.profile_id.
- `instrument/r01eq_person.json`: per-awardee supporting R01eq and R01eq_contact_PI indicators.
- `derived/funding_events.json` and `nih_funding_events.json`: per-awardee event lists with code, start and institute (ic); the latter supplies the NIH Data Book definition.
- `reporter/contemporaneous/*.json` and `reporter/historical/*.json`: saved `response.results` project lists for prior-award dates and own-grant matching. `construct.organizations` retrieves these captures.

Outcome builders run in order: `outcomes.leadership`, `outcomes.contemporaneous_variants`, `outcomes.historical` (pass pair-label and intent-label directories), `outcomes.trial_characteristics`, `outcomes.extended`, `outcomes.prior_trial_audit`, `outcomes.reporting`, `outcomes.seven_year`. All are invoked with `python -m`. Cohort keys, baseline eligibility, registry features, funding events and source captures must already exist. Never point these writers at the only copy of the frozen analytic inputs.


## Construction order

Run modules as `DATA_DIR=/path/to/private/inputs python -m construct.NAME`. All
construction outputs stay under `DATA_DIR`. Work on a copy of frozen inputs.
The sequence below describes dependencies; the incremental retrieval stages
require the listed existing source captures and curated manifests. Missing
manifests are errors, not evidence of no eligible records. No empty substitute
manifests are provided.

| Stage | Modules and outputs |
|---|---|
| Cohorts | `cohort`: RePORTER inventories, selected initial K awards, exclusions, prior-K checks, both ordered cohort keys, and the 80-person search key. Announcement lists and date filters are in the module; the earliest selected award per profile is retained. IDs combine a seeded stratified search sample and a SHA-256 ordering of the remaining profiles. |
| Eligibility | `baseline_packets`: masked abstract packets; `baseline`: frozen annotations, adjudications and scope rechecks to final baseline labels and contemporaneous eligibility/funding columns. |
| Organizations and grants | `organizations`: organization histories and saved project responses; `funding`: cohort funding pulls, R01-equivalent indicators and both funding-event definitions. |
| Current registry | `registry contemporaneous`, then `registry historical`: identical name/grant/institution queries and candidate filters, saved paginated responses and person-specific study lists. |
| Publication recovery | `seed_registry`, `publication_leads`, `publication_registry`, `sample_registry`: initial registry and 80-person publication searches. `pubmed`, then `publication_identity`: full-cohort article retrieval, author identity metadata, identity snapshot. `publication_metadata` contains the shared XML parser. |
| Archived registry | `snapshots`: downloads and verifies the deposits below. `archive_candidates`, `archive_compatibility`, `archive_responsible_parties`, `archive_fetch`: leads, matching-query flag, responsible-party leads and current records/aliases. These stages read an existing merged registry seed and review-case list. |
| Merged evidence | `merge_candidates`: combines current records, archived/publication leads, identifier aliases and curated timing corrections. `archive_evidence`, then `start_dates`: historical registry text and timing-conflict flags. |
| Documents | `protocols`: incremental protocol PDF retrieval/text extraction from the existing source manifest. `protocol_pages`, `protocol_ocr`, `protocol_encoded_ocr`: sparse/encoded-page OCR. `published_protocols`: PMC protocol text from the curated article inventory. |
| Leadership measurement | `screen_pairs`, `trial_people`, `leadership_packets`: deterministic name/timing rules, registry role metadata and contemporaneous evidence packets. `historical_packets`: the common registry-only candidate and screened packet sets for both periods. |
| Intent and scientific fields | `intent_packets`, `boundary_packets`, `lineage_packets`: masked K text and scientific trial fields. `seven_year_packets`: additional candidate packets for years five through seven. Boundary/lineage sampling requires the derived pair outcomes. |
| Outcomes and panel | Run measurement with frozen or newly acquired labels, then the outcome modules listed above. `trial_features` derives registry design/date/status features; it precedes trial-characteristic outcomes. `panel_roster` uses K-trial pairs and historical analytic eligibility; `ktrial_publications` retrieves NCT-indexed authorship; `registry_history.js` and `registry_history` supply the panel history input. |

`cohort`, `organizations`, `funding`, and registry/PubMed retrieval replay saved
responses when present; missing captures require network access. RePORTER
captures have `request`, `response` (with `results` and `meta.total`), and retrieval
metadata. ClinicalTrials.gov captures have `query`, `response.studies`, pagination
metadata, URL and retrieval timestamp. Current per-person records contain
`pi_id`, `blind_id`, `query`, `batch_query`, `status`, and `studies`; historical
records also record `name_fallback` (absent in some frozen captures means false).
The public search APIs are [NIH RePORTER](https://api.reporter.nih.gov/) and
[ClinicalTrials.gov](https://clinicaltrials.gov/data-api/api). PubMed and PMC use
[NCBI E-utilities](https://www.ncbi.nlm.nih.gov/books/NBK25501/).

Capture locations are `sources/reporter`, `sources/historical_reporter`,
`reporter/{contemporaneous,historical}`, `sources/{r01eq,funding,nih_funding}`,
`registry/historical`, `sources/ktrial_pubmed`, and `contemporaneous/sources`.
Keep request grouping, filenames and ordering from each reader when relocating
frozen captures. Capture and evidence manifests may contain absolute private paths or relative
`source_file` paths; relocate the referenced files and update all referencing
manifests together, retaining source/text hashes. These private paths do not belong in this tree.

## Frozen registry deposits

- [AACT 2022-11-09](https://zenodo.org/records/10091147): `AACT-2022-11-09.zip`,
  MD5 `1d4e6d141f40d300186fdd3d0a5980b1`; deposited 2023-11-09.
- [CTTI 2024-09-27](https://zenodo.org/records/13984069): `responsible_parties.txt`,
  MD5 `7a05bfb5f6e64ff8dad4ff0f8696ca35`; deposited 2024-10-23. This source supplies
  responsible parties, not a complete study record.

`snapshots` writes `AACT_20221109_archive_inventory.json` and
`aact_responsible_parties_manifest.json`: source URL, collection/deposit dates,
verified MD5 and, for the ZIP, member names, byte sizes and CRC values. These are
computed inventories of the downloaded files.

## Required annotation and correction manifests

All paths in this table are private. Except where stated otherwise, they are
under `contemporaneous/`. Store the supplied records with their actual provenance;
these files are required inputs, not annotations generated by retrieval code.

| File or family | Schema and use |
|---|---|
| `labels/baseline_A_*.json`, `baseline_QC_*.json`, `baseline_targeted_*.json` | Ordered arrays aligned to the corresponding `packets/baseline*.json`: `blind_id`, `reviewer_id`, `research_type`, `human_scope`, `intent_evidence`, `scope_evidence`, `rationale`. Evidence must be a literal substring of the masked abstract. Main, independent check and targeted sets contain 1,527, 374 and 452 records. |
| `labels/baseline_adjudicated.json`, `baseline_targeted_adjudicated_*.json`, `baseline_BESH_rechecked.json` | The same fields plus `adjudication_reason`; the scope-recheck set contains 46 records. Allowed intent/scope values are enforced by `baseline`; independent-check and targeted packet selection are supplied with the frozen annotations. |
| `cohort/trials_with_sample_search.json` (under `DATA_DIR`) | Ordered seed person records containing `pi_id`, `studies` in ClinicalTrials.gov API format, source/search metadata and publication leads; produced by the seed/publication search modules. |
| `trials_merged.json`, `review_cases.json` | Required incremental seed state: per-person merged API studies and person–trial cases with cohort identity, K dates/text/institution, `protocol`, source roles, timing and pending-review fields. The merger preserves the supplied per-person study order and appends newly retrieved identifiers in sorted order; archive retrieval reads this state. A bare cohort is not a substitute. |
| `publication_identity_snapshot.json` | Source-file SHA-256 map and identity audit reference, validated against article/capture inputs. `publication_identity` produces this with `publication_all_article_identity_audit.json`; rows distinguish linked articles, affiliations and pre-K publication dates. |
| `historical_start_exclusion_audit.json` | Object with `conflicts`: `blind_id`, `nct_id`, `historical_actual_start`, `historical_raw_study`, `historical_window`, `window`, `study_type`, `screen`. Supplies historically supported timing recovery. |
| `outcome_window_corrections.json` | Array: `case_id`, `K_start`, `end_5y`, `trial_start`, `old_screening_window`, `corrected_window`, `reason`. Flags source timing conflicts for deterministic screening. |
| `published_protocol_new_leads_audit.json`, `published_protocol_identifier_new_leads.json` | Arrays: `blind_id`, `nct_id`, `pmid`, `source`, and `prior_screen` for audited leads. These are curated additions to the candidate universe. |
| `archive_fetch_order.json` | Ordered array of registry identifiers establishing the saved retrieval order before the remaining eligible leads. Preserve order for capture filenames; do not invent priority entries. |
| `protocol_sources.json` | Incremental array: `nct_id`, `url`, `status`, `document_date`, `retrieved_at`, `local_text`, `pages`. Existing source rows are extended by `protocols`. |
| `protocol_publication_inventory.json` | Array: `pmid`, `pmcid`, `doi`, `title`, `nct_provenance`, `xml_source_file`; curated article–trial links for published protocols. |
| `protocol_publication_association_flags.json` | Array with `article_source` strings identifying article associations excluded from leadership evidence. Preserve the supplied rationale and ancillary fields. |
| `protocol_visual_addenda.json` | Curated visual text evidence: `addendum_id`, `nct_id`, `document_date_metadata`, `local_text`, `method`, `source_url`, `pdf_sha256`, `text_sha256`, `image_pages`. No automated visual-annotation producer is supplied. |
| `protocol_mixed_addenda.json`, `protocol_encoded_addenda.json`, `protocol_publication_addenda.json` | Generated text-evidence manifests with source identity, local text, method and hashes. OCR entries include page numbers; encoded entries may include reused OCR pages. Article entries include `pmid`, `pmcid`, publication dates and evidence kind. |

## Registry-history capture and compact schema

After `panel_roster`, run `construct/registry_history.js` in a ClinicalTrials.gov
browser console and select the private roster locally. The script sends only
registry identifiers to the site. Save its download under
`DATA_DIR/sources/registry_history.json`, then run `python -m construct.registry_history`.
The internal endpoints are `/api/int/studies/{id}?history=true` and
`/api/int/studies/{id}/history/{version}`. Direct requests return HTTP 403 in the
verification environment; the supplied capture uses browser-origin requests.
Browser retrieval remains environment dependent. The response structure also
appears in the [ctrdata history client](https://github.com/rfhb/ctrdata/blob/master/R/ctrLoadQueryIntoDbCtgov2.R).

The capture is an object keyed by registry identifier. Each value has
`retrieved_at`, `overview.history.changes` (entries with integer `version` and
submission `date`), and `versions` (one full response per indexed version).
A version response has `studyVersion` and `study.protocolSection`, including
`identificationModule`, `contactsLocationsModule.overallOfficials`,
`sponsorCollaboratorsModule.responsibleParty`, and `statusModule.overallStatus`.
Versions begin at zero. Duplicate or incomplete captures fail validation.

The compact object retains the initial PI/grant state and subsequent changes:
`ev = [[version, reserved, names, linked], ...]`. `version` is a zero-based integer;
`reserved` is an empty string, unused by the panel; `names` contains `O:`-prefixed
overall principal investigators and `R:`-prefixed principal/sponsor investigators;
`linked` is 0/1 for the K institute/serial in registry identification fields.
`rec` is 0/1 for any recruiting, enrolling-by-invitation, active-not-recruiting or
completed status across versions. Panel classifications use the order, initial
version, names, K link and recruitment flag, not dates in the reserved field.

The frozen compact input contains 596 trials and 911 events. Original raw
version captures are unavailable for parser verification here. The supplied
change-state compactor specifies a reproducible rule; exact event-selection
equivalence to the frozen compact file is unverified. Frozen compact inputs
support exact panel replay; newly retrieved histories constitute a new snapshot.
