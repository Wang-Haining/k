# Aggregate results

Fifty-three CSVs contain reported aggregate estimates and their supporting cells.
Directories follow the reported topics: `contemporaneous`, `historical`,
`registry_panel` (registration and execution), `reporting`, `lineage`,
`follow_up` (seven years), `funding`, `composition`, `validation`,
`supplementary` (additional S1 analyses), and `sensitivity` (additional analyses).
No row identifies a person or trial.
Validation agreement and accuracy use the pooled 280-dossier reference and the
intent, K/new boundary and lineage samples. Initial dossier-only scores stay
under `DATA_DIR/validation`; pooled agreement reports all available double ratings.

## Public reproduction

`make public` reads only the pseudonymized awardee tables in `data/public/`.
The IDs are pseudonymous, not anonymous; the inputs derive from public NIH
RePORTER and ClinicalTrials.gov records. It uses the existing analysis
models with institution bootstraps skipped, writes point estimates and supporting
counts to ignored `results/public/`, and verifies every value exactly against
these shipped CSVs. Original result files remain unchanged. The release was
verified with Python 3.12.13 and R 4.6.0: **27 CSVs, 426 exactly matching
point-estimate/supporting rows**. Public outputs omit intervals, standard errors,
bootstrap diagnostics, institution counts, and inferential test columns.

Institution-clustered intervals use cluster identifiers that are not released
and are available to editors and reviewers in confidence with the rest of the
confidential package. Contemporaneous Wilson/Newcombe intervals do not require
institution identifiers, but this public target consistently exports point
estimates and supporting counts only.

| Results directory | Files with point estimates/supporting counts reproduced |
|---|---|
| `contemporaneous/` | `estimates.csv`, `cumulative.csv`, `intent.csv` |
| `historical/` | `estimates.csv`, `leadership_estimates.csv`, `joint_leadership_estimates.csv`, `observed_cell_means.csv`, `ktrial_by_year.csv` |
| `registry_panel/` | `shares.csv`, `differences.csv` (awardee-level indicators) |
| `reporting/` | `ktrial_by_stratum.csv`, `estimates.csv` (awardee-level reporting) |
| `follow_up/` | `cells.csv`, `estimates.csv` |
| `funding/` | `estimates.csv` |
| `supplementary/` | `ktrial_cells.csv`, `new_trial_reporting.csv`, `registration_sensitivity_estimates.csv`, `contemporaneous_registration_shares.csv` |
| `validation/` | `validation_design.csv` |
| `sensitivity/` | `grant_link_estimates.csv`, `legacy_estimates.csv`, `covid_estimates.csv`, `registration_horizon_estimates.csv`, `cohort_trend_estimates.csv`, `funding_existing_estimates.csv`, `funding_broadened_estimates.csv` |

Both five- and seven-year registration-horizon contrasts are reproducible from
released derived indicators. Reconstructing those indicators from registry
submission dates and trial labels still requires the linked inputs. Likewise,
awardee-level panel contrasts are reproducible, but record-by-record registry
history, responsibility shifts, and publication matching cannot be audited from
the released flags. Models do not read shipped estimates as inputs; the shipped
CSVs are read only to verify public outputs.

The following are outside `make public`:

- `historical/prior_capacity.csv`: even point estimates require institution
  membership to construct institutional capacity.
- `validation/corrected_did.csv`: human-corrected point estimates are means of
  institution-bootstrap draws with imputation, so they also require the
  confidential cluster identifiers. A nonclustered imputation run would change
  the estimator and would not exactly reproduce these shipped values.
- `sensitivity/cohort_trend_bounds.csv`: interval envelopes and breakdown values
  require institution-bootstrap draws; the corresponding full-sample point
  estimates are reproduced in `cohort_trend_estimates.csv`.
- `lineage/estimates.csv` and `validation/lineage_corrected.csv`: trial/awardee
  linkage, scientific text, and lineage reference classifications are withheld.
- Trial reporting (`sensitivity/reporting_trial_cells.csv` and
  `reporting_trial_estimates.csv`), trial characteristics, prior-trial audits,
  and grant-link PI/judgment diagnostics: require trial-level records, dates,
  named registry roles, or pair-level labels. Awardee flags do not recover the
  unique-trial denominators or within-awardee overlap.
- Person-year hazard results in `supplementary/` and
  `sensitivity/covid_hazard_estimates.csv`: require the unreleased risk panel
  and supporting characteristic inputs; annual cumulative flags are insufficient.
- `composition/`: the full script requires additional prior-award and trial
  multiplicity/linkage sensitivity covariates omitted from this main-estimate
  release. Some simple cells or bounds can be reconstructed from released columns.
- Human accuracy/agreement scoring: the returned trial, boundary, lineage and
  adjudication workbooks are withheld. The released awardee human-reference
  states provide the correction labels, but do not contain institution clusters
  or all scoring-module inputs.
- `sensitivity/grant_link_cells.csv` is not automated by this target; its
  awardee component counts can be obtained from the released `k_id_field`,
  `k_text`, `k_none`, stratum and intent columns. Its existing writer also builds
  trial-level diagnostics and requires linked construction inputs.

The code for these analyses remains available, together with `construct/` for
public-source reconstruction and the input specifications for the confidential
reviewer package. Exact frozen-snapshot reproduction uses that package; current
public-source retrieval can change the source snapshot and model classifications.

## Columns and units

Each file's full header and unique row key appear below. Key columns are
categorical except fiscal/calendar year, follow-up year, and binary intent/post.
`estimate`, `RD`, `observed`, `did`, `difference` are point estimates; `lo`/`hi`,
`CI_low`/`CI_high` and `ci_low`/`ci_high` are 95% interval bounds. `se` is the
standard error, `mde80` the minimum detectable effect at 80% power, and `fisher_p*`
a two-sided Fisher test probability. `n*`, `events*`, `unknown*`, `known_excluded*`,
`sampled`, `cell_population`, `denominator_n`, `reps`, and `na_reps` are counts.
`ESS*`/`effective_n` are effective sample sizes. Accuracy weights are
inverse-sampling weights; their sums are represented population counts.
`status`, `interval_method`, `ci_method` describe estimation/interval availability.
Empty or NA cells are inapplicable or nonestimable, not zero.

- Contemporaneous `estimates`: `p1`, `p0`, `RD` and interval bounds are proportions;
  1 is Required and 0 Not Allowed. Cumulative `primary`/`secondary` and intent
  `pct_intent` are percentages; cumulative `year` is years since K start.
- Other outcome estimates and confidence limits are percentage points. Hazard
  contrasts are points per person-year; hazard calendar `event` and `n` are
  event and at-risk counts. `k23_hazards_by_calendar` contains no computed rate.
- Composition balance means/DIDs are proportions, except `inst_log_k` (log cohort
  K-award count per institution). Trimming shares are proportions. Exact-test
  `pre_intent`, `post_intent`, `pre_nointent`, `post_nointent` encode event/total counts, percentages and exact binomial confidence limits.
- Descriptive trial shares, registration/reporting shares, trajectory `ktrial_*`
  and `new_trial`, seven-year cell outcomes, and panel shares are percentages.
  `k_ktrial`, `k_new_trial`, `n_k_trials`, `n_trials`, `n_people` and denominators
  are counts; median enrollment is participants per trial. Audit `prior_trial_PI`,
  `prior_trial_is_K_trial`, and `prior_trial_only_K_trial` are counts.
- Agreement is percent and kappa is unitless. Accuracy Se/Sp/PPV/NPV and intervals
  are proportions. Corrected DIDs are points; corrected lineage levels are
  percentages and differences points. In lineage pair-share rows, `hi` stores
  the pair denominator as `n=<count>`; `lo` is empty. The share is in `ref_pct`.
  `validation_cells` in corrected lineage stores validation counts, not an effect.

## Codes

`primary`, `primary_main`, `new_trial`, `new_protocol`, and `first new trial`
refer to a distinct new trial led after the K start; `secondary`, `secondary_main`
and `any_trial` include the original K trial. `K_trial`, `original_K`, and
`ktrial_direct` identify the K trial; `ktrial_direct` requires qualifying PI
leadership within five years. `own_trial_planned`/`intent` denote baseline
own-trial planning; `developed_from_K`/`developed_new_trial` denote scientific
lineage from K work. All are binary endpoints before aggregation.

`ktrial_any_start` removes the start-window restriction; `ktrial_grant_linked`
requires a matching K identifier; `ktrial_judged_unlinked` uses a K classification
without a grant link. `primary_judgment_only`/`primary_link_only` vary how the
K/new boundary is determined. `primary_nihdef` applies the NIH clinical-trial
definition. `_fdaaa` restricts to drug/biologic/device interventions; `_4y` or
`_window_4y` uses four years; `_7y` uses seven. `_timely` means registration within
12 months of trial start; `primary_late` starts in years four–five. `_excl_*`
excludes basic-science, source-start-conflict or withdrawn/zero-enrollment cases;
`_registry_roles_only` and `_current_record_only` restrict evidence sources.
`two_plus_trials` requires at least two led trials; `nonpi_multisite` denotes
non-PI participation in a multisite trial.

`informative_new_trial`/`informative_strict`, `multisite_new_trial`,
`nih_funded_new_trial`, `industry_new_trial`, `completed_with_results`,
`nih_new_trial`, and `nih_new_trial_own_grant` are trial-characteristic endpoints;
exact design thresholds and grant matches are in `outcomes/trial_characteristics.py`
and `outcomes/extended.py`. `_due_results` refers to completed trials due for
reporting with posted results; `_due_results12` requires results within 12 months
of primary completion. `new_trial_due_results12` is conditional on a due new trial.

`R01`, `R34`, `U01`, `any_funding` refer to initial awards within five years.
`R01eq` comprises R01/R37/R35/DP2, with `_contact_PI` restricting
contact role. `R01nih` comprises DP1/DP2/DP5/R01/R37/R56/RF1/RL1/U01 plus R35 from GM/HG; `_R35` includes all R35,
while the base definition includes R35 only from GM/HG. `_or_trialgrant` adds
R61/R33/UG3/UH3. `_5y`/`_7y` are funding windows. `_and_`/`_without_` combine or
exclude trial/funding outcomes.

`preK_PI_nonK` is prior non-K trial leadership; `prior_nih_pi_award` and
`prior_research_grant` are pre-K funding indicators. `pre_early` is earlier
announcements with pre-2018 starts, `pre_legacy` earlier announcements with
2018–2019 starts, `post`/`post_policy` new announcements, and `pre_policy` both
earlier-announcement strata. `intent=0/1` is the baseline planning indicator.
`ktrial_only`, `new_trial`, `none` identify joint validation sampling states.

Panel `a_pi_from_registration`, `b_link_added_later_or_never`,
`c_responsibility_shift`, `d_insufficient` are mutually exclusive registration
categories. `v0` is initial registry version; `klink` is a K grant link; `other_pi`
is another PI. `has_k_trial` uses intent-awardee denominators; remaining panel
shares also use intent-awardee denominators. `awardee_first_last` is first/last
authorship on an indexed trial publication. `dev_*`, `pairshare_*`, `diff_*`
encode developed-trial levels, pair shares and post-minus-reference differences.

`eligible_main` excludes BESH-only abstracts; `eligible_no_mixed` also excludes
mixed applied/BESH abstracts. `all_eligible`, `baseline_applied_human_scope`,
`common_year_IC_support`, and `preK_trial_PI_0/1` specify analysis populations.
`population_id` joins mechanism, eligibility, endpoint and population with `__`.
`raw` is an unadjusted contrast; `pooled_standardized` standardizes across
fiscal-year/institute cells. DID is difference in differences; FY is fiscal year,
IC institute/center, FE fixed effects, IPW inverse-probability weighting.
`human_centered`, `human_jeffreys`, `human_swap`, `human_rater_a/b` and
`human_plus_intent_by_outcome/stratum` identify the correction variants detailed
below; `observed` is the uncorrected estimate.
`dossier_trial` denotes trial rows within a dossier. `rater_a` and `rater_b` are
neutral identities preserving assignment and reference-rater roles.

## File schemas

### `composition/balance.csv`

8 rows. Key: `mechanism`, `covariate`.

Columns: `mechanism`, `covariate`, `mean_pre_intent`, `mean_post_intent`, `mean_pre_nointent`, `mean_post_nointent`, `did`, `lo`, `hi`.

### `composition/estimates.csv`

20 rows. Key: `analysis`, `mechanism`, `outcome`, `spec`.

Columns: `analysis`, `mechanism`, `outcome`, `spec`, `estimate`, `lo`, `hi`, `se`, `mde80`, `n`, `na_reps`.

### `composition/k08_exact.csv`

4 rows. Key: `mechanism`, `outcome`.

Columns: `mechanism`, `outcome`, `pre_intent`, `post_intent`, `fisher_p_intent_change`, `pre_nointent`, `post_nointent`, `fisher_p_nointent_change`.

### `composition/trimming_bounds.csv`

4 rows. Key: `mechanism`, `outcome`, `bound`.

Columns: `mechanism`, `outcome`, `bound`, `trimmed_share`, `estimate`, `lo`, `hi`.

### `contemporaneous/cumulative.csv`

20 rows. Key: `mechanism`, `group`, `year`.

Columns: `mechanism`, `group`, `n`, `year`, `primary`, `secondary`.

### `contemporaneous/estimates.csv`

76 rows. Key: `population_id`, `method`.

Columns: `mechanism`, `eligibility`, `endpoint`, `population`, `population_id`, `method`, `n1`, `n0`, `unknown1`, `unknown0`, `known_excluded1`, `known_excluded0`, `events1`, `events0`, `p1`, `p0`, `RD`, `CI_low`, `CI_high`, `ESS1`, `ESS0`, `fisher_p`, `status`, `interval_method`.

### `contemporaneous/intent.csv`

4 rows. Key: `mechanism`, `group`.

Columns: `mechanism`, `group`, `n_intent`, `n`, `pct_intent`.

### `follow_up/cells.csv`

8 rows. Key: `mechanism`, `post`, `intent`.

Columns: `mechanism`, `post`, `intent`, `n`, `new_trial_5y`, `new_trial_7y`.

### `follow_up/estimates.csv`

6 rows. Key: `analysis`, `mechanism`, `outcome`, `spec`.

Columns: `analysis`, `mechanism`, `outcome`, `spec`, `estimate`, `lo`, `hi`, `se`, `mde80`, `n`, `na_reps`.

### `funding/estimates.csv`

22 rows. Key: `analysis`, `mechanism`, `outcome`, `spec`.

Columns: `analysis`, `mechanism`, `outcome`, `spec`, `estimate`, `lo`, `hi`, `se`, `mde80`, `n`, `na_reps`.

### `historical/estimates.csv`

26 rows. Key: `mechanism`, `estimand`, `outcome`, `sample`.

Columns: `mechanism`, `estimand`, `outcome`, `sample`, `estimate`, `lo`, `hi`, `n`, `na_reps`.

### `historical/joint_leadership_estimates.csv`

6 rows. Key: `mechanism`, `quantity`.

Columns: `mechanism`, `quantity`, `estimate`, `lo`, `hi`, `n`, `na_reps`.

### `historical/ktrial_by_year.csv`

37 rows. Key: `mechanism`, `intent`, `fiscal_year`, `period`.

Columns: `mechanism`, `intent`, `fiscal_year`, `period`, `n`, `ktrial_direct`, `ktrial_grant_linked`, `new_trial`, `k_ktrial`, `k_new_trial`.

### `historical/leadership_estimates.csv`

50 rows. Key: `analysis`, `mechanism`, `outcome`, `spec`.

Columns: `analysis`, `mechanism`, `outcome`, `spec`, `estimate`, `lo`, `hi`, `se`, `mde80`, `n`, `na_reps`.

### `historical/observed_cell_means.csv`

2 rows. Key: `mechanism`, `outcome`.

Columns: `mechanism`, `outcome`, `observed`.

### `historical/prior_capacity.csv`

6 rows. Key: `analysis`, `mechanism`, `outcome`, `spec`.

Columns: `analysis`, `mechanism`, `outcome`, `spec`, `estimate`, `lo`, `hi`, `se`, `mde80`, `n`, `na_reps`.

### `lineage/estimates.csv`

9 rows. Key: `quantity`, `comparison`.

Columns: `quantity`, `comparison`, `post_pct`, `ref_pct`, `difference`, `lo`, `hi`.

### `registry_panel/differences.csv`

34 rows. Key: `quantity`, `comparison`.

Columns: `quantity`, `comparison`, `estimate`, `lo`, `hi`.

### `registry_panel/shares.csv`

3 rows. Key: `stratum`.

Columns: `stratum`, `n_intent_awardees`, `has_k_trial`, `a_pi_from_registration`, `b_link_added_later_or_never`, `c_responsibility_shift`, `d_insufficient`, `v0_awardee_pi`, `other_pi_v0`, `awardee_added_later`, `klink_v0`, `klink_added_later`, `started`, `completed`, `completed_within_5y`, `stopped`, `results`, `published`, `awardee_first_last`.

### `reporting/estimates.csv`

4 rows. Key: `analysis`, `mechanism`, `outcome`, `spec`.

Columns: `analysis`, `mechanism`, `outcome`, `spec`, `estimate`, `lo`, `hi`, `se`, `mde80`, `n`, `na_reps`.

### `reporting/ktrial_by_stratum.csv`

3 rows. Key: `stratum`.

Columns: `stratum`, `n_intent`, `n_due_k_trial`, `pct_due_of_intent`, `results_posted_pct`, `results_12mo_pct`.

### `supplementary/contemporaneous_registration_shares.csv`

4 rows. Key: `mechanism`, `group`.

Columns: `mechanism`, `group`, `n`, `ktrial_timely`, `primary_timely`, `nih_new_trial`, `nih_new_trial_own_grant`, `n_due`, `results12_among_due`.

### `supplementary/hazard_descriptives.csv`

4 rows. Key: `mechanism`, `group`.

Columns: `mechanism`, `group`, `n`, `pct_k_trial_registered_as_PI`, `n_new_trial_PIs`, `pct_new_trial_PIs_with_NIH_funded_trial`, `pct_new_trial_PIs_with_industry_trial`, `pct_informative`, `pct_R01eq`.

### `supplementary/hazard_estimates.csv`

46 rows. Key: `analysis`, `mechanism`, `outcome`, `spec`.

Columns: `analysis`, `mechanism`, `outcome`, `spec`, `estimate`, `lo`, `hi`, `n`, `na_reps`.

### `supplementary/k23_hazards_by_calendar.csv`

36 rows. Key: `cal_year`, `intent`, `post`.

Columns: `cal_year`, `intent`, `post`, `event`, `n`.

### `supplementary/ktrial_audit.csv`

10 rows. Key: `mechanism`, `category`.

Columns: `mechanism`, `n_required`, `n_without_k_trial`, `category`, `n`.

### `supplementary/ktrial_cells.csv`

8 rows. Key: `mechanism`, `period`, `intent`.

Columns: `mechanism`, `period`, `intent`, `n`, `ktrial_direct`, `ktrial_any_start`, `ktrial_grant_linked`, `ktrial_judged_unlinked`, `any_trial`, `new_trial`, `new_trial_without_ktrial`.

### `supplementary/ktrial_characteristics.csv`

4 rows. Key: `mechanism`, `period`.

Columns: `mechanism`, `period`, `n_k_trials`, `median_enrollment`, `enrollment_ge100_pct`, `randomized_pct`, `multisite_ge3_pct`, `phase2plus_pct`, `completed_pct`, `terminated_or_withdrawn_pct`, `ongoing_pct`, `n_completed_due`, `results_posted_among_due_pct`, `registered_within_12mo_of_start_pct`.

### `supplementary/new_trial_characteristics.csv`

12 rows. Key: `analysis`, `mechanism`, `cell`.

Columns: `analysis`, `mechanism`, `cell`, `n_people`, `n_trials`, `median_enrollment`, `pct_randomized`, `pct_pilot_titled`, `pct_enrollment_ge100`, `n_completed_due`, `pct_results_posted_among_due`.

### `supplementary/new_trial_reporting.csv`

4 rows. Key: `mechanism`, `group`.

Columns: `mechanism`, `group`, `n_with_due_new_trial`, `pct_with_results_posted`.

### `supplementary/prior_trial_audit.csv`

4 rows. Key: `mechanism`, `group`.

Columns: `mechanism`, `group`, `n`, `prior_trial_PI`, `prior_trial_is_K_trial`, `prior_trial_only_K_trial`, `prior_trial_PI_excluding_K_trial_pct`.

### `supplementary/registration_sensitivity_estimates.csv`

28 rows. Key: `analysis`, `mechanism`, `outcome`, `spec`.

Columns: `analysis`, `mechanism`, `outcome`, `spec`, `estimate`, `lo`, `hi`, `se`, `mde80`, `n`, `na_reps`.

### `validation/agreement.csv`

3 rows. Key: `module`, `field`, `comparison`.

Columns: `module`, `field`, `comparison`, `n_total`, `n_compared`, `n_excluded`, `percent_agreement`, `kappa`, `status`.

### `validation/corrected_did.csv`

64 rows. Key: `variant`, `quantity`. Columns: `variant`, `quantity`,
`estimate`, `lo`, `hi`, `n`, `reps`. Eight variants each report K, new,
K-minus-new, any (the K/new union), neither, K only, new only, and both DIDs.
The four mutually exclusive joint-state DIDs sum to zero before rounding.

Rated awardees retain resolved human states. Unrated/unresolved outcomes use
stratum x instrument intent x instrument joint-state Dirichlet cells; a refined
cell without resolved ratings borrows its three-state parent counts. The centered
prior assigns 0.5 to the instrument state and 0.01 to each alternative; Jeffreys
assigns 0.5 to each. `human_swap` changes the assigned rater on the 40 additional
overlap dossiers. Rater A/B variants also replace adjudication on the initial
70 double-rated dossiers; all variants retain the sole available rating for
single-rated dossiers. Intent variants retain resolved human intent, then impute
other intents within instrument call x instrument any-trial state (pooled across
strata) or stratum x instrument call, using a centered Beta prior (0.5 on the
instrument call, 0.01 on the alternative). Reference counts remain fixed outside
resampling. Each variant uses 2,000 institution-bootstrap draws; corrected point
estimates are draw means. These are model-based reclassification sensitivities.

### `validation/instrument_accuracy.csv`

64 rows. Key: `module`, `outcome`, `stratum`, `intent`, `metric`.

Columns: `module`, `outcome`, `stratum`, `intent`, `metric`, `n_sampled`, `n_resolved`, `n_excluded`, `excluded_weight`, `denominator_n`, `denominator_weight`, `effective_n`, `estimate`, `ci_low`, `ci_high`, `ci_method`, `status`.

### `validation/lineage_corrected.csv`

9 rows. Key: `quantity`.

Columns: `quantity`, `estimate`, `lo`, `hi`, `reps`.

### `validation/pooled_accuracy.csv`

84 rows. Key: `module`, `outcome`, `stratum`, `intent`, `metric`.

Columns: `module`, `outcome`, `stratum`, `intent`, `metric`, `n_sampled`, `n_resolved`, `n_excluded`, `excluded_weight`, `denominator_n`, `denominator_weight`, `effective_n`, `estimate`, `ci_low`, `ci_high`, `ci_method`, `status`.

### `validation/pooled_agreement.csv`

7 rows. Key: `module`, `field`, `comparison`.

Columns: `module`, `field`, `comparison`, `n_total`, `n_compared`, `n_excluded`, `percent_agreement`, `kappa`, `status`.

### `validation/validation_design.csv`

18 rows. Key: `stratum`, `intent`, `instrument_state`.

Columns: `stratum`, `intent`, `instrument_state`, `cell_population`, `sampled`.

## Additional sensitivity analyses

`outcomes/revision.py` derives private outcomes; `analysis/revision.R` produces
aggregate estimates. Historical analyses exclude BESH-only awardees and use
`outcome ~ intent * post + factor(year) + factor(ic)`, with 1,000 institution
resamples, seed 2026, and percentile intervals. Outcomes in each specification
share draws, including K-minus-new. Point estimates use the full sample.
K23 is primary; legacy, COVID, horizon-registration and funding results also
include K08. Existing CSVs are retained unchanged.

Unless specified below, estimate files have columns `mechanism`, `outcome`,
`spec`, `estimate`, `lo`, `hi`, `n`, `n_pre`, `n_post`,
`n_institutions`, `na_reps`; the key is mechanism x outcome x spec. Estimates
are percentage points. `n_pre/n_post` apply to historical contrasts and are NA
for reporting and contemporaneous comparisons. Nonestimable bootstrap draws
are counted, as in existing analyses; fewer than 95% finite draws fails the run.

### Grant-link decomposition

- `sensitivity/grant_link_cells.csv`: 18 rows; key stratum x intent x component;
  columns stratum, intent, component, n, events, share_pct. Shares count awardees
  with any qualifying K trial in each component; components may overlap across
  an awardee's different trials.
- `sensitivity/grant_link_judgments.csv`: 22 nonempty cells; key stratum x intent
  x link x judgment; columns stratum, intent, link, judgment, n_pairs. These are
  qualifying five-year leadership pairs, including K and new trials.
- `sensitivity/grant_link_estimates.csv`: 6 adjusted K23 DIDs, for the three
  components and K/new/K-minus-new ignoring free-text support.
- `sensitivity/grant_link_pi.csv`: 9 rows; key stratum x pi_of_record; columns
  stratum, pi_of_record, n_awardees, n_with_any_linked, n_with_category, share_pct,
  candidate_records. Denominators are all eligible K23 trial-intent awardees.
  All K-linked candidate records are included, without start-window or leadership
  screening (469 records: 456 interventional and 13 observational). Current Overall Official PI and Responsible Party investigator fields
  define awardee / other_person / no_pi_named. Awardee matching uses the existing
  name guard restricted to those current qualifying fields. Awardee takes precedence
  if co-listed with another PI. Record categories are exclusive; awardee shares can
  overlap. No assertion is made about the PI at initial registration.

The historical `k_link` field checks only the identification module. It has no
free-text-qualified pairs, unlike the contemporaneous screen. Thus ignoring
free-text support reproduces historical endpoints exactly. `none` here means
no recorded identification-module serial; it is not an independent search proving
absence of serials throughout free text. Component DIDs need not sum to the total
K DID because awardees can qualify through multiple components.

### Legacy and COVID

`sensitivity/legacy_estimates.csv`: 18 rows. K/new/any/K-minus-new DIDs using
FY2018-2019 legacy awards as pre, with either all post awardees or only FY2018-2019
post awardees. The existing calendar-start >= 2018-01-01 restriction is separately
reproduced for K; its point estimate and sample size must match the committed row.
Bootstrap intervals differ with the draw sequence.

`sensitivity/covid_estimates.csv`: 6 rows. K/new/K-minus-new five-year DIDs
exclude trial starts during 2020-2021 from the outcome, retaining all awardees.
This changes calendar exposure and is a sensitivity, not a pandemic-free causal
comparison. `sensitivity/covid_hazard_estimates.csv`: 4 rows copied exactly from
`supplementary/hazard_estimates.csv` for the calendar x intent specification and
for excluding 2020-2021 person-years. Its columns match that file plus n_awardees;
`n` counts person-years, and estimates are percentage points per person-year.
The calendar x intent row also includes years-since-K and institute effects;
the person-year exclusion row uses common calendar, years-since-K and institute
effects, as in the existing analysis.

### Cohort trends

`sensitivity/cohort_trend_estimates.csv`: 9 K23 rows; key outcome x spec;
columns outcome, spec, estimate, lo, hi, n, n_pretrend, na_reps. For K, new and
K-minus-new, it reports the original DID, differential pre-cohort slope, and DID
after extrapolating that slope. Pretrend estimation uses FY2014-2017 pre-policy
cohorts, with intent, year FE, institute and intent x (year - 2017). Subtract the
estimated differential slope times intent x (year - 2017) from every outcome,
then fit the usual DID. Both stages are refitted in the same institution draw.
Slope units are percentage points/year; other rows are percentage points.

`sensitivity/cohort_trend_bounds.csv`: 24 rows; key outcome x spec x M_pp_per_year;
columns outcome, spec, M_pp_per_year, estimate, lo, hi, drift_exposure_years,
breakdown_pp_per_year, n, reps. A Rambachan-Roth-inspired linear-drift envelope
allows an additional intent-specific constant slope deviation of up to +/-M
points/year after FY2017: bias regressor = intent x max(year - 2017, 0).
The usual DID coefficient of that regressor is the exposure in years. Each draw
re-estimates both the pretrend and this exposure; the interval takes percentile
bounds of the lower/upper shifted estimates. Both the original and pretrend-extrapolated DIDs are bounded. The grid is
0, 0.5, 1, 2; breakdown
is the smallest M making the interval include zero, found by bisection. Zero
means the unperturbed interval for that specification already includes zero. This is
an explicit additive-bias sensitivity, not formal HonestDiD robust inference;
these award-cohort outcomes are not uncontaminated pre-treatment outcome leads.
See the [HonestDiD authors' description](https://github.com/asheshrambachan/HonestDiD)
for the distinction from their smoothness and relative-magnitude restrictions.

### Trial-level reporting

`sensitivity/reporting_trial_cells.csv`: 3 rows keyed by stratum; columns
stratum, n_k_trials, n_due, n_terminated_due, n_within12, within12_pct,
n_ever_submitted, ever_submitted_pct, n_unknown_pcd_passed, n_missing_pcd.
All unique five-year K trials of eligible K23 trial-intent awardees are included.
No trial is duplicated within/across strata in these inputs (asserted).
Due = COMPLETED, or TERMINATED with ACTUAL enrollment > 0, and primary completion
at least 12 calendar months before frozen retrieval (2026-09-27).
Month-only completion dates use the first day, consistent with existing date
normalization. Primary-completion ACTUAL/ESTIMATED type is absent from the analytic
features and is not imposed. UNKNOWN records with a past completion date are
counted separately, not included in the due denominator.

Both within-12-month and ever-reporting use results_first_submitted, not the
post-QC has_results field. Thus “ever” means ever submitted, not verified public
posting. `sensitivity/reporting_trial_estimates.csv`: 10 rows, the two shares
in each stratum and post-minus-early/legacy differences. Shares are percentages;
differences are percentage points. These are unadjusted trial-level estimates,
with institution resampling; n counts trials.

### Symmetric registration horizon

`sensitivity/registration_horizon_estimates.csv`: 8 rows, five- and seven-year
new-trial DIDs with original and symmetric registration rules, using exactly the
same complete seven-year-follow-up sample. Symmetric endpoints require first
submission no later than K start + the respective horizon. Additional year-5–7
labels and packet hashes are checked, and original seven-year outcomes must
reconcile awardee by awardee. Five-year symmetric outcomes are nested in seven-year
symmetric outcomes. No absent-at-retrieval trial is inferred.

### Independent funding

`sensitivity/funding_existing_estimates.csv`: 10 rows, copied without changing
numbers from `funding/estimates.csv` for R01nih_5y and
R01nih_or_trialgrant_5y. Columns and keys match the source. R01-equivalent uses
R01, R37, R56, RF1, RL1, U01, DP1, DP2, DP5, plus R35 at NIGMS/NHGRI.
The existing broadened definition adds R61, R33, UG3 and UH3, but **does not
include R34**. Both historical adjusted DID and contemporaneous unadjusted RD
already exist; R01-equivalent also has a contemporaneous adjusted RD.

`sensitivity/funding_broadened_estimates.csv`: 6 rows. The requested definition
unions R01nih_or_trialgrant_5y with the supplied five-year R34 indicator. It reports
historical adjusted DIDs and contemporaneous unadjusted and FY/institute-adjusted
Required-minus-Not Allowed RDs, for K23 and K08. No grant event reconstruction or
new funding retrieval is required.
