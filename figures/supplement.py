"Assemble S1–S12 Tables and supplementary definitions from public aggregates."

import csv
import re
from decimal import ROUND_HALF_UP, Decimal

from config import RESULTS_DIR, ROOT

A = RESULTS_DIR
LABELS = {
    "primary": "New-trial leadership",
    "primary_main": "New-trial leadership",
    "secondary": "Any-trial leadership, including the K trial",
    "secondary_main": "Any-trial leadership, including the K trial",
    "primary_window_4y": "New-trial leadership within four years",
    "primary_4y": "New-trial leadership within four years",
    "primary_excl_basic_science": "New-trial leadership excluding basic-science primary purpose",
    "primary_excl_withdrawn_zero": "New-trial leadership excluding withdrawn trials with zero enrollment",
    "primary_excl_start_conflict": "New-trial leadership excluding conflicting start dates",
    "primary_registry_roles_only": "New-trial leadership using registry roles only",
    "primary_current_record_only": "New-trial leadership using the current record only",
    "primary_fdaaa": "New-trial leadership in drug, biologic or device trials",
    "multisite_new_trial": "New-trial leadership in trials with at least three sites",
    "completed_with_results": "New-trial leadership in completed trials with posted results",
    "nih_funded_new_trial": "NIH-funded new-trial leadership",
    "industry_new_trial": "Industry-funded new-trial leadership",
    "ktrial_direct": "K-trial leadership within five years",
    "larger_trial_strict": "Larger-trial leadership",
    "primary_nihdef": "New-trial leadership under the NIH clinical-trial definition",
    "primary_late": "New-trial leadership starting at least three years after K start",
    "nonpi_multisite": "Non-PI participation in a multisite trial",
    "ktrial_direct_fdaaa": "K-trial leadership in drug, biologic or device trials",
    "ktrial_timely": "K-trial leadership with registration within 12 months of trial start",
    "primary_timely": "New-trial leadership with registration within 12 months of trial start",
    "nih_new_trial": "New-trial leadership citing an NIH grant",
    "nih_new_trial_own_grant": "New-trial leadership citing a grant on which the awardee is PI",
    "new_trial_due_results12": "Results submitted within 12 months of primary completion",
    "ktrial_any_start": "K-trial leadership including trials started before K start",
    "ktrial_grant_linked": "K-trial leadership citing the K grant",
    "grant_linked": "K-trial leadership citing the K grant",
    "ktrial_judged_unlinked": "K-trial leadership judged from the K plan without a grant link",
    "judged_unlinked": "K-trial leadership judged from the K plan without a grant link",
    "any_trial": "Any-trial leadership",
    "new_trial": "New-trial leadership",
    "new_trial_without_ktrial": "New-trial leadership without K-trial leadership",
    "R01nih_5y": "R01-equivalent award within five years (NIH definition)",
    "R01nih_7y": "R01-equivalent award within seven years (NIH definition)",
    "two_plus_trials": "Leadership of at least two distinct trials",
    "primary_judgment_only": "New-trial leadership using scientific distinctness alone",
    "primary_link_only": "New-trial leadership using absence of a K-grant link alone",
    "all_eligible": "All eligible awardees",
    "baseline_applied_human_scope": "Awardees with an assigned human intervention",
    "raw": "Unadjusted",
    "unadjusted": "Unadjusted",
    "BASIC_SCIENCE": "basic science",
    "n_people": "Awardees in group, n",
    "n_trials": "New trials, n",
    "median_enrollment": "Median enrollment",
    "pct_randomized": "Randomized (%)",
    "randomized_pct": "Randomized (%)",
    "pct_pilot_titled": "Pilot-titled (%)",
    "pct_enrollment_ge100": "Enrollment at least 100 (%)",
    "enrollment_ge100_pct": "Enrollment at least 100 (%)",
    "n_completed_due": "Completed trials due for reporting, n",
    "pct_results_posted_among_due": "Results posted among trials due (%)",
    "results_posted_among_due_pct": "Results posted among trials due (%)",
    "pct_k_trial_registered_as_PI": "K-trial leadership (%)",
    "n_new_trial_PIs": "New-trial leaders, n",
    "pct_new_trial_PIs_with_NIH_funded_trial": "New-trial leaders with NIH-funded trials (%)",
    "pct_new_trial_PIs_with_industry_trial": "New-trial leaders with industry-funded trials (%)",
    "cal_year": "Calendar year",
    "fiscal_year": "Fiscal year",
    "n_with_due_new_trial": "Awardees with a new trial due for reporting, n",
    "n_due": "Awardees with a new trial due for reporting, n",
    "pct_with_results_posted": "Awardees with results posted (%)",
    "results12_among_due": "Results submitted within 12 months among awardees with a trial due (%)",
    "n_required": "Required awardees, n",
    "n_without_k_trial": "Required awardees without a K trial, n",
    "prior_trial_PI": "Prior trial leadership, n",
    "prior_trial_is_K_trial": "Prior leadership included the K trial, n",
    "prior_trial_only_K_trial": "Prior leadership was limited to the K trial, n",
    "prior_trial_PI_excluding_K_trial_pct": "Prior leadership of a non-K trial (%)",
    "k_ktrial": "K-trial leaders, n",
    "k_new_trial": "New-trial leaders, n",
    "n_k_trials": "First K trials, n",
    "multisite_ge3_pct": "At least three sites (%)",
    "phase2plus_pct": "Phase 2 or higher (%)",
    "completed_pct": "Completed (%)",
    "terminated_or_withdrawn_pct": "Terminated or withdrawn (%)",
    "ongoing_pct": "Ongoing (%)",
    "registered_within_12mo_of_start_pct": "Registered within 12 months of start (%)",
    "preK_PI_nonK": "Prior non-K trial leadership",
    "prior_nih_pi_award": "Prior NIH award as PI",
    "prior_research_grant": "Prior NIH research grant",
    "inst_log_k": "Log number of cohort K awards at the institution",
    "mean_pre_intent": "Pre-policy, trial intent",
    "pre_intent": "Pre-policy, trial intent",
    "mean_post_intent": "Post-policy, trial intent",
    "post_intent": "Post-policy, trial intent",
    "mean_pre_nointent": "Pre-policy, no trial intent",
    "pre_nointent": "Pre-policy, no trial intent",
    "mean_post_nointent": "Post-policy, no trial intent",
    "post_nointent": "Post-policy, no trial intent",
    "trimmed_share": "Trimmed proportion",
    "fisher_p_intent_change": "Fisher P, trial-intent group",
    "fisher_p_nointent_change": "Fisher P, no-intent group",
    "pre_policy": "Pre-policy",
    "pre policy": "Pre-policy",
    "post_policy": "Post-policy",
    "post policy": "Post-policy",
    "post": "Post-policy",
    "pre_early": "Early pre-policy",
    "pre early": "Early pre-policy",
    "pre_legacy": "Legacy-announcement",
    "pre legacy": "Legacy-announcement",
    "spec": "Model specification",
    "lo": "Lower 95% CI",
    "hi": "Upper 95% CI",
    "mde80": "Minimum detectable effect (80% power)",
    "did": "DID",
    "instrument_state": "Instrument classification",
    "cell_population": "Awardees in cell, n",
    "sampled": "Sampled awardees, n",
    "ktrial_only": "K trial only",
    "none": "No qualifying trial",
    "Module": "Validation component",
    "Module/outcome": "Validated outcome",
    "dossier dossiers": "Awardee dossiers",
    "dossier trial fields": "Candidate-trial records",
    "intent intent": "Trial-intent abstracts",
    "boundary K/new": "K/new boundary pairs",
    "lineage lineage": "Lineage pairs",
    "k relationship": "Relationship to the K study",
    "mechanism": "Mechanism",
    "endpoint": "Outcome",
    "outcome": "Outcome",
    "eligibility": "Eligibility",
    "population": "Population",
    "method": "Method",
    "analysis": "Analysis",
    "cell": "Group",
    "group": "Group",
    "estimand": "Comparison",
    "sample": "Population or model",
    "estimate": "Estimate",
    "n": "Sample size",
    "intent": "Trial intent",
    "period": "Period",
    "stratum": "Stratum",
    "covariate": "Covariate",
    "category": "Category",
    "bound": "Bound",
    "lower": "Lower",
    "upper": "Upper",
    "all": "All",
    "overall": "Overall",
    "n (Req/NA)": "Required / Not Allowed, n",
    "Required %": "Required (%)",
    "Not Allowed %": "Not Allowed (%)",
    "year FE + IC": "Fiscal-year and institute adjustment",
    "adjusted for FY + IC": "Fiscal-year and institute adjustment",
    "years-since-K FE + calendar FE + IC": "Time-since-K and calendar-year fixed effects, plus institute",
    "+ calendar x intent FE": "Plus calendar-year by intent fixed effects",
    "+ calendar x intent + years-since-K x intent FE": (
        "Plus calendar-year by intent and time-since-K by intent fixed effects"
    ),
    "E0 intent share post-pre": "Post-minus-pre change in trial-intent share",
    "E1 portfolio level change (trend + IC)": "Portfolio level change (time trend and institute adjustment)",
    "E3 FY2018 DID intent x post": "Fiscal-year 2018 DID, intent by period",
    "E3 FY2018 intent awardees post vs pre FOA": (
        "Fiscal-year 2018 trial-intent awardees, new versus earlier announcements"
    ),
    "K start 2018, intent=1": "K start in 2018, trial intent",
    "FDAAA-like trials only": "Drug, biologic or device trials only",
    "intent x post x K08, year FE + IC": "Intent by period by K08, with fiscal-year and institute adjustment",
    "reweighted to pre-policy covariates (IPW), IC FE": (
        "Inverse-probability weighted to pre-policy covariates, with institute fixed effects"
    ),
    "adjusted for prior non-K trial PI + FY + IC": (
        "Adjusted for prior non-K trial leadership, fiscal year and institute"
    ),
    "FY2018 same-year contrast": "Fiscal-year 2018 same-year contrast",
    "intent awardees, new vs legacy FOA": "Trial-intent awardees, new versus legacy announcements",
    ("pre-policy limited to 2018-19 legacy-FOA award starts (application dates unverified)"): (
        "Pre-policy limited to 2018–2019 legacy award starts (application dates unverified)"
    ),
    "Placebo DID intent x (2016-17 vs 2014-15), pre only": "Placebo DID, 2016–2017 versus 2014–2015, pre-policy only",
    "Placebo level change 2016, pre only": "Placebo level change in 2016, pre-policy only",
}


def reader_tables(text):
    out, headers, table = ([], [], 0)
    for line in text.splitlines():
        heading = re.match("## S(\\d+) Table\\.", line)
        if heading:
            table = int(heading[1])
        if not line.startswith("|"):
            headers = []
            out.append(line)
            continue
        cells = [c.strip() for c in line.split("|")[1:-1]]
        is_header = not headers
        if is_header:
            headers = cells
        assert len(cells) == len(headers), f"S{table}: expected {len(headers)} cells, got {len(cells)}: {line}"
        if all(re.fullmatch("-+", c) for c in cells):
            widths = {
                "endpoint": 32,
                "outcome": 32,
                "spec": 32,
                "estimand": 30,
                "sample": 28,
                "eligibility": 22,
                "population": 25,
                "analysis": 20,
                "mechanism": 10,
                "RD (95% CI)": 24,
                "category": 30,
                "Outcome within 5 years of K start": 60,
                "Estimate (percentage points)": 60,
            }
            out.append("| " + " | ".join("-" * widths.get(h, 14) for h in headers) + " |")
            continue
        shown = []
        for column, value in zip(headers, cells, strict=False):
            label = LABELS.get(value, value)
            if is_header and table == 3 and (value == "n"):
                label = "Awardees in group, n"
            if (
                is_header
                and table == 3
                and (
                    value
                    in (
                        "ktrial_direct",
                        "ktrial_any_start",
                        "ktrial_grant_linked",
                        "ktrial_judged_unlinked",
                        "any_trial",
                        "new_trial",
                        "new_trial_without_ktrial",
                    )
                )
            ):
                label += " (%)"
            if not is_header and column.lower() == "intent" and (value in ("0", "1")):
                label = {"0": "No trial intent", "1": "Trial intent"}[value]
            if table == 5 and value == "new_trial":
                label = "New trial, with or without a K trial"
            if not is_header and re.fullmatch(r"-?\d+(?:\.\d+)?", value):
                percent = (
                    "pct" in column.lower()
                    or "%" in column
                    or column
                    in (
                        "estimate",
                        "lo",
                        "hi",
                        "mde80",
                        "did",
                        "ktrial_direct",
                        "ktrial_any_start",
                        "ktrial_grant_linked",
                        "ktrial_judged_unlinked",
                        "any_trial",
                        "new_trial",
                        "new_trial_without_ktrial",
                        "grant_linked",
                        "judged_unlinked",
                        "results12_among_due",
                        "ktrial_timely",
                        "primary_timely",
                        "nih_new_trial",
                        "nih_new_trial_own_grant",
                    )
                )
                balance = table == 4 and "covariate" in headers and column not in ("mechanism", "covariate")
                if balance or column == "trimmed_share":
                    scale = 1 if "inst_log_k" in cells else 100
                    label = f"{float(value) * scale:.{3 if scale == 1 else 1}f}"
                elif column == "event" or percent:
                    digits = 2 if column == "event" or any("hazard" in c.lower() for c in cells) else 1
                    label = f"{float(value):.{digits}f}"
                elif column == "median_enrollment" and float(value).is_integer():
                    label = str(int(float(value)))
            label = re.sub("^(?:E[0-3]:?|(?:dossier|intent|boundary|lineage):)\\s+", "", label)
            if not is_header and column == "estimand" and label == "DID":
                label = "Historical DID"
            label = re.sub("\\bFY\\b", "fiscal year", label)
            label = re.sub("\\bFE\\b", "fixed effects", label)
            label = re.sub("\\bICs\\b", "Institutes", label)
            label = re.sub(r"\bIC\b", "institute", label)
            label = re.sub(r"\bFY(?=\d)", "Fiscal year ", label)
            label = label.replace(" x ", " × ")
            label = re.sub("\\bFOA\\b", "announcement", label)
            label = re.sub(r"(?<![\w])-(?=\d)", "−", label)
            label = label.replace("historical DID", "Historical DID").replace(
                "contemporaneous RD", "Contemporaneous RD"
            )
            if label and "a" <= label[0] <= "z":
                label = label[0].upper() + label[1:]
            assert "_" not in label, f"unmapped label in S{table}: {value}"
            shown.append(label)
        out.append("| " + " | ".join(shown) + " |")
    return polish_layout("\n".join(out) + "\n")


def polish_layout(text):
    headings = {
        1: ["Five-year leadership"],
        2: ["Estimates"],
        3: ["Leadership by period"],
        4: ["Covariate balance", "Excess-share trimming scenario"],
        5: ["Validation sample"],
        6: ["Human agreement", "Instrument accuracy"],
        7: ["Leadership estimates", "Scientific continuity"],
        8: [
            "Grant-link components",
            "Adjusted component contrasts",
            "Current PI of record",
        ],
        9: ["Legacy comparisons"],
        10: ["Cohort trends", "Bounded-drift envelopes"],
        11: [
            "Trial-level reporting denominators and shares",
            "Trial-level contrasts",
        ],
        12: ["Registration by horizon"],
    }
    short = {
        "Awardees in group, n": "Awardees, n",
        "Sample size": "N",
        "Model specification": "Model",
        "Population or model": "Population / model",
        "Required / Not Allowed, n": "Group sizes, n",
        "Minimum detectable effect (80% power)": "MDE",
        "Completed trials due for reporting, n": "Due trials, n",
        "Results posted among trials due (%)": "Results posted (%)",
        "Enrollment at least 100 (%)": "Enrollment ≥100 (%)",
        "K-trial leadership within five years (%)": "K trial (%)",
        "K-trial leadership including trials started before K start (%)": "Any-start K trial (%)",
        "K-trial leadership citing the K grant (%)": "Grant-linked K trial (%)",
        "K-trial leadership judged from the K plan without a grant link (%)": "Unlinked K trial (%)",
        "Any-trial leadership (%)": "Any trial (%)",
        "New-trial leadership (%)": "New trial (%)",
        "New-trial leadership without K-trial leadership (%)": "New only (%)",
        "K-trial leaders, n": "K-trial PIs, n",
        "New-trial leaders, n": "New-trial PIs, n",
        "Pre-policy, trial intent": "Pre, intent",
        "Post-policy, trial intent": "Post, intent",
        "Pre-policy, no trial intent": "Pre, no intent",
        "Post-policy, no trial intent": "Post, no intent",
        "Fisher P, trial-intent group": "P, intent",
        "Fisher P, no-intent group": "P, no intent",
        "Trimmed proportion": "Trimmed (%)",
        "Instrument classification": "Instrument state",
        "Awardees in cell, n": "Population, n",
        "Sampled awardees, n": "Sample, n",
        "First new-trial rate (% per person-year)": "Rate (% / person-year)",
        "Outcome within 5 years of K start": "Outcome within 5 years",
        "Estimate (percentage points)": "Outcome or model",
        "K23 Required vs Not Allowed, %": "K23 groups (%)",
        "K08 Required vs Not Allowed, %": "K08 groups (%)",
        "Validated outcome": "Outcome",
        "Resolved / sample": "Resolved / total",
        "Awardees with a new trial due for reporting, n": "Awardees due, n",
        "Awardees with results posted (%)": "Results posted (%)",
        "Required awardees, n": "Required, n",
        "Required awardees without a K trial, n": "Without K trial, n",
    }
    sections = re.split(r"(?m)(?=^## )", text)
    for i, section in enumerate(sections):
        match = re.match(r"## S(\d+) Table\.", section)
        if not match:
            continue
        table, panel = int(match[1]), 0

        def render(match, table=table):
            nonlocal panel
            rows = [[c.strip() for c in line.split("|")[1:-1]] for line in match[0].splitlines()]
            headers, data = rows[0], rows[2:]
            notes = []
            if table == 1:
                notes.append("Group sizes: Required / Not Allowed.")
            estimate = "Estimate" if "Estimate" in headers else "DID"
            if all(h in headers for h in (estimate, "Lower 95% CI", "Upper 95% CI")):
                e, lo, hi = (headers.index(h) for h in (estimate, "Lower 95% CI", "Upper 95% CI"))
                for row in data:
                    row[e] = f"{row[e]} ({row[lo]} to {row[hi]})"
                headers[e] = f"{estimate} (95% CI)"
                for j in sorted((lo, hi), reverse=True):
                    headers.pop(j)
                    for row in data:
                        row.pop(j)
            for j in reversed(range(len(headers))):
                values = {r[j] for r in data}
                if len(values) == 1 and next(iter(values)) and not next(iter(values)).startswith("**"):
                    notes.append(f"{short.get(headers[j], headers[j])}: {next(iter(values))}.")
                    headers.pop(j)
                    for row in data:
                        row.pop(j)
            headers = [short.get(h, h) for h in headers]
            if table == 4 and panel == 0:
                notes.append(
                    "Binary covariates: percentages; DID and CI: percentage points. Institutional size: log units."
                )
            if "MDE" in headers:
                notes.append("MDE: minimum detectable effect at 80% power.")
            widths = [max(12, min(40, max(len(r[j]) for r in [headers] + data))) for j in range(len(headers))]
            for j, h in enumerate(headers):
                if h in ("Outcome", "Characteristic", "Model", "Population / model", "Outcome or model"):
                    widths[j] = 42
                elif h in ("Mechanism", "N", "MDE"):
                    widths[j] = 14 if h == "Mechanism" else 12
                elif "95% CI" in h:
                    widths[j] = 27
            result = f"**{chr(65 + panel)}. {headings[table][panel]}**\n\n"
            result += "\n".join("| " + " | ".join(r) + " |" for r in [headers, ["-" * w for w in widths]] + data) + "\n"
            panel += 1
            return result + ("\n" + " ".join(reversed(notes)) + "\n" if notes else "")

        sections[i] = re.sub(r"(?m)(?:^\|.*\n)+", render, section)
        assert panel == len(headings[table]), (table, panel)
    return "".join(sections)


def md(rows, cols=None):
    cols = cols or list(rows[0])
    out = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]

    def cell(v):
        return str(v).replace("|", " / ")

    return "\n".join(out + ["| " + " | ".join(cell(r.get(c, "")) for c in cols) + " |" for r in rows]) + "\n"


def csvrows(p):
    return list(csv.DictReader(p.open()))


def main():
    title = (
        "NIH's dedicated K23 trial pathway was associated with more K-trial leadership "
        "but no detectable gain in new trials"
    )
    parts = ["# S1 Text. Measurement instrument and human validation\n\n" + title + ".\n"]
    parts.append(
        "## eMethods 1. Measurement instrument and human validation\n\n**Candidate "
        "retrieval.** NIH RePORTER supplied the award cohorts, with trial outcomes "
        "retrieved from ClinicalTrials.gov by September 2026. Searches combined the "
        "awardee's given name and surname, K grant identifiers, and surname with "
        "institution. Current registry records were supplemented by archived records from "
        "November 2022 and September 2024; the latter contributed responsible-party "
        "information only.\n\n**Screening rules.** Trial start dates were assessed within the"
        " inclusive window from K start through five years later. Study type, K-grant "
        "linkage, and withdrawal with zero enrollment were determined by rule. Name "
        "matching required a surname with a compatible given name or initial within four "
        "tokens; pairs failing the guard cannot qualify.\n\n**Trial review.** Qwen/Qwen3.8-27B-FP8 was"
        " run locally on K abstracts and current and archived registry records to classify "
        "identity, leadership, intervention scope, and relationship to the K study. "
        "Protocol or published-protocol excerpts were also used in the contemporaneous "
        "analysis. All contemporaneous candidate pairs were reviewed. In the historical "
        "comparison, candidate pairs passing the name and timing screen were reviewed; the "
        "rest were classified as not qualifying by rule. The same registry sources and "
        "classification rules were used in both historical periods.\n\n**Trial intent and "
        "validation.** Qwen/Qwen3.8-27B-FP8 classified K abstracts with funding-designation phrases "
        "masked as proposing an awardee-led interventional study, a mentor-led trial, other"
        " research, or unclear. The own-trial classification defined intent in the awarded, policy-responsive abstract."
        " The leadership prompt was developed on held-out calibration pairs and frozen before "
        "the full run and human validation. Stored labels record prompt, schema and packet hashes. "
        "Weights and serving-container digests were not pinned, so new inference is a new measurement. "
        "Human validation design, agreement, instrument accuracy, and corrected estimates "
        "appear in S5–S7 Tables. Code, prompts and the rating codebook are available in "
        "the code repository.\n\n**Table conventions.** PI denotes principal investigator; "
        "DID, difference in differences; RD, risk difference; and CI, confidence interval. "
        "Unless otherwise stated, outcome windows extend from K start through five years "
        "later.\n\n"
    )
    parts.append(
        "## Cohort-flow reconciliation\n\nThe contemporaneous and historical analyses retain "
        "their distinct eligibility rules and the same follow-up requirements. The table "
        "distinguishes the separate baseline review used for the contemporaneous cohort "
        "from the common abstract-classifier exclusion used in both historical periods.\n\n| "
        "Analysis or stage | Awardees or awards | Definition |\n|---|---|---|\n| "
        "Earlier-announcement cohort | 1,860 | K08 and K23 awards starting from 2014 under "
        "the earlier parent announcements |\n| Contemporaneous cohort before exclusion | "
        "1,527 | K08 and K23 awards under the new announcements |\n| Contemporaneous "
        "eligibility | 1,527 - 26 = 1,501 | Separate baseline review excludes "
        "basic-experimental-only projects |\n| Contemporaneous K23 | 825 = 358 + 467 | "
        "Required plus Not Allowed awardees under the baseline-review rule |\n| Combined "
        "historical comparison before exclusion | 1,860 + 1,527 = 3,387 | Earlier and new "
        "announcement regimes |\n| Common historical eligibility | 3,387 - 25 = 3,362 | "
        "Common abstract-classifier exclusion in both periods |\n| Historical K23 | 1,847 = "
        "375 + 635 + 346 + 491 | Earlier intent, earlier no intent, post-policy intent, "
        "post-policy no intent |\n| Historical post-policy K23 | 837 = 346 + 491 | "
        "Common-classifier rule, compared with 825 under the separate baseline review |\n| "
        "Historical K23 trial-intent panel | 721 = 301 + 74 + 346 | Early, legacy and "
        "post-policy intent awardees, including those without a registered K trial |\n\nThe "
        "825 versus 837 counts reflect different exclusions, not different follow-up "
        "requirements. Legacy awards are identified by 2018–2019 award starts under PA-16 "
        "parent announcements. Their timing suggests likely dissemination-policy coverage, "
        "but application dates were not verified per award. Differences between displayed "
        "rates use unrounded estimates.\n"
    )
    est = [
        r
        for r in csvrows(A / "contemporaneous" / "estimates.csv")
        if r["method"] == "raw"
        and r["eligibility"] == "eligible_main"
        and r["population"] == "all_eligible"
        and r["endpoint"] in ("primary_main", "secondary_main")
    ]

    def pct(v):
        return f"{100 * float(v):.1f}" if v not in ("", "NA") else ""

    rows = [
        {
            "mechanism": r["mechanism"],
            "endpoint": r["endpoint"],
            "eligibility": {
                "eligible_main": "Main eligibility",
                "eligible_no_mixed": "excluding mixed applied/basic projects",
            }.get(r["eligibility"], r["eligibility"]),
            "population": r["population"],
            "method": r["method"],
            "n (Req/NA)": f"{r['n1']}/{r['n0']}",
            "Required %": pct(r["p1"]),
            "Not Allowed %": pct(r["p0"]),
            "RD (95% CI)": f"{pct(r['RD'])} ({pct(r['CI_low'])} to {pct(r['CI_high'])})",
        }
        for r in est
    ]
    parts.append(
        (
            "## S1 Table. Contemporaneous Required versus Not Allowed comparison "
            "{#s1-table.-contemporaneous-required-versus-not-allowed-comparison}\n\n"
            "Leadership within five years of K start among all eligible awardees. Risk differences and "
            "confidence limits are percentage points.\n\n"
        )
        + md(rows)
    )
    leadership = {
        (r["mechanism"], r["outcome"]): r
        for r in csvrows(A / "historical" / "leadership_estimates.csv")
        if r["analysis"] == "historical DID" and r["spec"] == "year FE + IC"
    }
    funding = {
        (r["mechanism"], r["outcome"]): r
        for r in csvrows(A / "funding" / "estimates.csv")
        if r["analysis"] == "historical DID"
    }
    fdaaa = next(
        r
        for r in csvrows(A / "historical" / "leadership_estimates.csv")
        if r["analysis"] == "historical DID" and r["mechanism"] == "K23" and r["outcome"] == "ktrial_direct_fdaaa"
    )
    e8 = [
        fdaaa,
        leadership["K23", "primary_late"],
        funding["K23", "R01nih_5y"],
        leadership["K08", "primary"],
        leadership["K08", "ktrial_direct"],
    ]
    parts.append(
        (
            "## S2 Table. Further historical estimates "
            "{#s2-table.-further-historical-estimates}"
            "\n\nHistorical DIDs adjust for fiscal year and institute. Estimates and confidence limits are "
            "percentage points, and minimum detectable effects assume 80% power. The drug, biologic or device "
            "restriction counts only K trials testing those interventions. Late-start new trials begin "
            "at least three years after K start. R01-equivalent awards within five years follow the NIH Data "
            "Book definition: DP1, DP2, DP5, R01, R37, R56, RF1, RL1 and U01, plus R35 from NIGMS or NHGRI only. "
            "K08 estimates rest on 14 pre-policy trial-intent awardees.\n\n"
        )
        + md(e8, ["analysis", "mechanism", "outcome", "spec", "estimate", "lo", "hi", "mde80", "n"])
    )
    cells = [
        {k: r[k] for k in ("mechanism", "period", "intent", "n", "ktrial_direct", "new_trial", "any_trial")}
        for r in csvrows(A / "supplementary" / "ktrial_cells.csv")
        if r["mechanism"] == "K23"
    ]
    parts.append(
        (
            "## S3 Table. Leadership by period and trial intent "
            "{#s3-table.-leadership-by-period-and-trial-intent}"
            "\n\nInstrument-measured leadership within five years of K start. Percentages count awardees. "
            "K trials either cite the K grant or are judged to match the K plan.\n\n"
        )
        + md(cells)
    )
    parts.append(
        (
            "## S4 Table. Composition checks {#s4-table.-composition-checks}\n\n"
            "The first panel reports baseline covariates by trial intent and announcement regime, with the "
            "intent-by-period DID for each covariate. Binary covariate means are percentages, and covariate DIDs "
            "and confidence limits are percentage points. Institutional size is the log number of cohort K "
            "awards. The second panel removes the post-policy excess intent membership from the top or bottom "
            "of the outcome distribution. This trimming scenario assumes added membership without displacement "
            "and an unchanged comparator, so it does not bound arbitrary funding selection. Trimming bounds and "
            "their confidence limits are percentage points.\n\n"
        )
        + md([r for r in csvrows(A / "composition" / "balance.csv") if r["mechanism"] == "K23"])
        + "\n"
        + md(csvrows(A / "composition" / "trimming_bounds.csv"))
    )

    human = A / "validation"
    design = csvrows(human / "validation_design.csv")
    assert len(design) == 18 and sum(int(r["sampled"]) for r in design) == 280, (
        "validation sample differs from 280 in 18 cells"
    )
    assert sum(int(r["cell_population"]) for r in design) == 1847, "validation population differs from 1847"
    parts.append(
        (
            "## S5 Table. Human validation design\n\nA stratified random sample of 280 "
            "historical K23 awardee dossiers represents 1,847 awardees across cells defined by "
            "stratum, baseline intent, and instrument state. Cell sizes targeted a 95% "
            "half-width of about 13 percentage points for the human-corrected K-trial DID. Two "
            "authors (HF and ZT) rated independently, blinded to announcement group, period labels, "
            "and model output, with ClinicalTrials.gov as the only trial-review source. Review"
            " included fresh name searches for missed trials, and funding-designation phrases "
            "were masked in award abstracts. Raters saw K start dates and project numbers needed "
            "for the five-year window and linkage, so timing and intent remained inferable. Of 110 "
            "double-rated dossiers, 70 used first-author resolution of disagreements and 40 "
            "used a reference rater randomly assigned before rating, while 170 were "
            "single-rated.\n\nA qualifying trial required an assigned intervention intended to "
            "prevent, diagnose, treat, or manage a condition or improve care, together with "
            "qualifying PI leadership. Measurement-only interventions did not meet this scope "
            "definition, even if the registry classified the study as interventional. K trials "
            "were grant-linked or judged to match the K plan, and new trials were unlinked and "
            "judged distinct, within five years of K start. The new-trial instrument state "
            "permits concurrent K-trial leadership. Six of 280 unclear awardee reference states"
            " were excluded from joint outcome correction cell counts, while the swapped-rater "
            "analysis excluded seven. Small cell sizes constrain precision, and human "
            "validation does not directly cover the additional seven-year observations.\n\nIntent"
            " is the instrument's baseline own-trial classification. Cell populations and "
            "sample sizes sum to 1,847 and 280, respectively.\n\n"
        )
        + md(design)
    )
    agreement = [
        r
        for r in csvrows(human / "pooled_agreement.csv")
        if r["module"] in ("dossier_all_double_rated", "dossier_trial_all_double_rated")
    ]
    agreement += [r for r in csvrows(human / "agreement.csv") if r["module"] in ("intent", "boundary", "lineage")]
    assert len(agreement) == 10, f"expected 10 agreement fields, got {len(agreement)}"
    labels = {
        "dossier_all_double_rated": "dossier dossiers",
        "dossier_trial_all_double_rated": "dossier trial fields",
        "intent": "intent intent",
        "boundary": "boundary K/new",
        "lineage": "lineage lineage",
    }
    ag = [
        {
            "Module": labels[r["module"]],
            "Field": r["field"].replace("_", " "),
            "Rated": r["n_total"],
            "Compared": r["n_compared"],
            "Agreement (%)": f"{float(r['percent_agreement']):.1f}",
            "κ": f"{float(r['kappa']):.2f}",
        }
        for r in agreement
    ]
    accuracy = csvrows(human / "pooled_accuracy.csv")
    accuracy += [
        r
        for r in csvrows(human / "instrument_accuracy.csv")
        if r["module"] in ("intent", "boundary", "lineage")
        and (r["stratum"] == "overall" or r["module"] in ("lineage", "intent"))
    ]
    outcomes = {
        "K_trial": "K trial",
        "new_trial": "New trial",
        "any_trial": "Any trial",
        "own_trial_planned": "Trial intent",
        "new_protocol": "New protocol",
        "original_K": "Original K",
        "developed_from_K": "Developed from K",
    }
    acc = {}
    for r in accuracy:
        assert r["status"] in ("ok", "zero_denominator"), f"unresolved accuracy metric: {r}"
        key = (r["module"], r["outcome"], r["stratum"], r["intent"])
        row = acc.setdefault(
            key,
            {
                "Module/outcome": r["module"] + ": " + outcomes[r["outcome"]],
                "Stratum": r["stratum"].replace("_", " "),
                "Intent": r["intent"],
                "Resolved / sample": r["n_resolved"] + "/" + r["n_sampled"],
            },
        )
        if r["status"] == "zero_denominator":
            assert r["denominator_n"] == "0" and r["estimate"] == "", r
            row[r["metric"] + " (95% CI)"] = "Not estimable: zero denominator"
        else:
            row[r["metric"] + " (95% CI)"] = (
                f"{float(r['estimate']):.2f} ({float(r['ci_low']):.2f} to {float(r['ci_high']):.2f})"
            )
    parts.append(
        (
            "## S6 Table. Human agreement and instrument accuracy\n\nAgreement covers all 110 "
            "double-rated dossiers and their 283 candidate-trial records, plus intent in 100 "
            "abstracts, K/new classification in 60 pairs, and lineage in 60 pairs. Agreement is"
            " between independent human raters, before reference-label resolution, and includes"
            " the full categorical fields. Accuracy compares instrument calls with the human "
            "reference, weighted by inverse sampling fractions, with Wilson intervals using "
            "Kish effective sample sizes. Outcome-specific unresolved references are excluded "
            "separately for accuracy, so its denominators differ from joint-state correction "
            "counts. Se is sensitivity, Sp specificity, PPV positive predictive value, and NPV "
            "negative predictive value. All leadership strata and intent groups are shown, "
            "together with stratum-specific intent, overall K/new accuracy and period-specific lineage "
            "accuracy.\n\nReported measurement validity rests on this blinded human sample. "
            "Qwen/Qwen3.8-27B-FP8 measured intent and person--trial status, and GPT-5.6 Sol rated "
            "lineage. Model lineage calls overstated continuity, especially in the pre-policy "
            "period.\n\nAgreement uses independent human ratings; accuracy uses the corresponding"
            " human reference labels.\n\n"
        )
        + md(ag)
        + "\n"
        + md(list(acc.values()))
    )
    corrected = csvrows(human / "corrected_did.csv")
    assert len(corrected) == 64, "expected 64 joint-state DID rows"

    def d1(value):
        return str(Decimal(str(value)).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))

    def ci(r):
        return f"{d1(r['estimate'])} ({d1(r['lo'])} to {d1(r['hi'])})"

    variants = {
        "observed": "Instrument",
        "human_centered": "Human: centered",
        "human_jeffreys": "Human: Jeffreys",
        "human_swap": "Human: swapped overlap rater",
        "human_rater_a": "Human: rater A for double-rated dossiers",
        "human_rater_b": "Human: rater B for double-rated dossiers",
        "human_plus_intent_by_outcome": "Human plus intent: instrument outcome state, pooled strata",
        "human_plus_intent_by_stratum": "Human plus intent: stratum and instrument call",
    }
    estimates = []
    for r in corrected:
        assert r["n"] == "1847" and r["reps"] == "2000", "unexpected correction sample or draws"
        if r["quantity"].endswith("-state DID") and r["variant"] != "human_centered":
            continue
        estimates.append({"Variant": variants[r["variant"]], "Quantity": r["quantity"], "Estimate (95% CI)": ci(r)})
    lineage = [r for r in csvrows(human / "lineage_corrected.csv") if r["quantity"] != "validation_cells"]
    assert len(lineage) == 8, f"expected eight corrected lineage estimates, got {len(lineage)}"
    lineage_names = {
        "dev_post": "Awardee share: post",
        "dev_pre_early": "Awardee share: early",
        "dev_pre_legacy": "Awardee share: legacy",
        "diff_pre_early": "Awardee difference: post minus early",
        "diff_pre_legacy": "Awardee difference: post minus legacy",
        "pairshare_post": "Pair share: post",
        "pairshare_pre_early": "Pair share: early",
        "pairshare_pre_legacy": "Pair share: legacy",
    }
    parts.append(
        (
            "## S7 Table. Instrument-measured and human-corrected estimates\n\nDIDs retain the "
            "same fiscal-year and institute-adjusted linear probability models in all 1,847 "
            "historical K23 awardees, with joint institution resampling for paired outcomes. "
            "Rated awardees retain their resolved human joint state (neither, K only, new only, "
            "or both). Unrated or unresolved states are imputed within stratum x instrument intent "
            "x instrument joint-state cells; empty refined cells borrow their three-state parent. "
            "The centered Dirichlet prior places 0.5 on the instrument state and 0.01 on each "
            "alternative; Jeffreys places 0.5 on each state. Swapping changes the assigned rater "
            "for the 40 overlap dossiers. Rater A and B variants additionally replace adjudication "
            "on the 70 initial double-rated dossiers; single-rated dossiers keep their sole rating. "
            "Intent sensitivities retain resolved human intent and impute other intents using "
            "either instrument call x instrument any-trial state (pooled across strata), or "
            "stratum x instrument call, with a centered Beta prior (0.5 on the call, 0.01 on "
            "the alternative). These are assumption-dependent reclassification sensitivities. "
            "Reference counts remain fixed while posterior draws represent calibration uncertainty. "
            "All variants use 2,000 institution-bootstrap draws and percentile intervals; corrected "
            "point estimates are draw means. Joint-state DIDs are shown for the centered correction and sum to "
            "zero before rounding. "
            "The instrument any-trial state here is the union of K and new trial leadership.\n\n"
            "Lineage correction draws binary developed-from-K statuses within period × K-trial "
            "availability × model-call cells, using a centered Beta prior inside 2,000 "
            "institution-bootstrap draws. The prior places 0.5 on the model call and 0.01 on "
            "the alternative. Awardee shares use all trial-intent awardees as denominators, "
            "while pair shares describe rated new-trial records. Units are percentage points "
            "for DIDs and differences and percentages for shares.\n\nInstrument estimates and "
            "human-corrected estimates use the outcome definitions and validation procedures "
            "described above.\n\n"
        )
        + md(estimates)
        + "\n"
        + md([{"Lineage quantity": lineage_names[r["quantity"]], "Estimate (95% CI)": ci(r)} for r in lineage])
    )
    strata = {"pre_early": "Early", "pre_legacy": "Legacy", "post": "Post-policy"}
    outcomes = {
        "ktrial_direct": "K trial",
        "primary": "New trial",
        "secondary": "Any trial",
        "k_minus_new": "K minus new",
    }
    components = {
        "id_field": "Identification module",
        "text": "Free text only",
        "none": "Judged from plan, no recorded serial",
    }
    rows = [
        {
            "Stratum": strata[r["stratum"]],
            "Trial intent": "Yes" if r["intent"] == "1" else "No",
            "Component": components[r["component"]],
            "Awardees": r["n"],
            "Events": r["events"],
            "Share (%)": d1(r["share_pct"]),
        }
        for r in csvrows(A / "sensitivity/grant_link_cells.csv")
    ]
    link_names = {
        "k_id_field": "K trial with identification-module link",
        "k_text": "K trial with free-text-only link",
        "k_none": "K trial judged from plan without serial",
    }
    estimates = [
        {"Outcome": link_names[r["outcome"]], "DID (95% CI)": ci(r), "N": r["n"]}
        for r in csvrows(A / "sensitivity/grant_link_estimates.csv")
        if r["outcome"] in link_names
    ]
    pi = [
        {
            "Stratum": strata[r["stratum"]],
            "PI of record": {"awardee": "Awardee", "other_person": "Another person", "no_pi_named": "No PI named"}[
                r["pi_of_record"]
            ],
            "Intent awardees": r["n_awardees"],
            "Any linked record": r["n_with_any_linked"],
            "Category awardees": r["n_with_category"],
            "Share (%)": d1(r["share_pct"]),
            "Candidate records": r["candidate_records"],
        }
        for r in csvrows(A / "sensitivity/grant_link_pi.csv")
    ]
    parts.append(
        "## S8 Table. Grant-link decomposition and PI of record\n\n"
        "Historical K-grant matching uses the identification module, with no free-text-only qualification. "
        "No recorded serial means no identification-module link, rather than a search proving its absence "
        "throughout free text. "
        "Component awardee shares can overlap across trials, so component DIDs need not sum to the total. "
        "PI diagnostics use current fields on all linked candidate records, including observational records "
        "and records outside the outcome window. "
        "Awardee PI takes precedence when co-listed with another person. Record categories are exclusive, "
        "while awardee categories may overlap. "
        "Shares use all intent awardees as denominators and do not establish initial PI designation or "
        "actual responsibility. "
        "Component contrasts use fiscal-year and institute adjustment with 1,000 institution draws.\n\n"
        + md(rows)
        + "\n"
        + md(estimates)
        + "\n"
        + md(pi)
    )
    legacy_specs = {
        "FY2018-2019 legacy pre; all post; five-year outcomes": "FY2018–2019 legacy versus all post",
        "FY2018-2019 legacy and post; five-year outcomes": "FY2018–2019 in both regimes",
    }
    rows = [
        {
            "Mechanism": r["mechanism"],
            "Comparison": legacy_specs[r["spec"]],
            "Outcome": outcomes[r["outcome"]],
            "DID (95% CI)": ci(r),
            "Pre / post, n": f"{r['n_pre']} / {r['n_post']}",
        }
        for r in csvrows(A / "sensitivity/legacy_estimates.csv")
        if r["mechanism"] == "K23" and r["outcome"] in ("ktrial_direct", "primary") and r["spec"] in legacy_specs
    ]
    parts.append(
        "## S9 Table. Legacy-only and same-calendar comparisons\n\n"
        "All outcomes use five years from K start and fiscal-year and institute adjustment. "
        "The comparison restricted to fiscal years 2018–2019 in both regimes is the primary check against "
        "concurrent policies and pandemic exposure. "
        "It aligns calendar exposure while leaving selection into announcements and shared policy effects unresolved. "
        "Intervals use 1,000 institution draws.\n\n" + md(rows)
    )
    trend_specs = {
        "original": "No-trend model",
        "pretrend_slope": "Differential early-cohort slope",
        "pretrend_extrapolated": "Extrapolated early-cohort trend",
    }
    trends = [
        {
            "Outcome": outcomes[r["outcome"]],
            "Model": trend_specs[r["spec"]],
            "Estimate (95% CI)": ci(r),
            "Units": "Points per year" if r["spec"] == "pretrend_slope" else "Percentage points",
            "N": r["n"],
            "Early-cohort n": r["n_pretrend"],
        }
        for r in csvrows(A / "sensitivity/cohort_trend_estimates.csv")
        if r["spec"] == "pretrend_extrapolated" and r["outcome"] in ("ktrial_direct", "primary")
    ]
    placebo = next(
        r
        for r in csvrows(A / "historical" / "leadership_estimates.csv")
        if r["analysis"] == "historical placebo DID" and r["mechanism"] == "K23" and r["outcome"] == "ktrial_direct"
    )
    trends.append(
        {
            "Outcome": "K trial",
            "Model": "Early-cohort placebo, fiscal years 2016–2017 versus 2014–2015",
            "Estimate (95% CI)": ci(placebo),
            "Units": "Percentage points",
            "N": placebo["n"],
            "Early-cohort n": placebo["n"],
        }
    )
    bounds = [
        {
            "Outcome": outcomes[r["outcome"]],
            "Model": trend_specs[r["spec"]],
            "Annual drift bound": r["M_pp_per_year"],
            "DID envelope (95%)": ci(r),
            "Interval breakdown, points/year": r["breakdown_pp_per_year"],
        }
        for r in csvrows(A / "sensitivity/cohort_trend_bounds.csv")
        if r["outcome"] == "ktrial_direct" and r["spec"] == "original"
    ]
    parts.append(
        "## S10 Table. Cohort trends and bounded drift\n\n"
        "Fiscal-year 2014–2017 intent-specific slopes adjust for year and institute. Subtracting this slope "
        "before refitting the DID gives the extrapolated estimate. Both stages are refitted in 1,000 "
        "institution draws. The drift envelope permits additional intent-specific annual drift after "
        "fiscal year 2017, retaining trend and exposure uncertainty. Breakdown denotes the annual bound "
        "where the interval first includes zero. These additive-bias envelopes are not formal robust "
        "event-study confidence sets. Early-cohort follow-up extends into the policy era, precluding "
        "uncontaminated pre-policy outcome leads. The placebo compares the trial-intent gap in fiscal years "
        "2016–2017 with 2014–2015 among early awards only.\n\n" + md(trends) + "\n" + md(bounds)
    )
    trial = csvrows(A / "sensitivity/reporting_trial_cells.csv")
    characteristics = {
        "n_k_trials": "Unique K trials",
        "n_due": "Due trials",
        "n_terminated_due": "Terminated due trials",
        "n_within12": "Submitted within 12 months, n",
        "within12_pct": "Submitted within 12 months (%)",
        "n_ever_submitted": "Ever submitted, n",
        "ever_submitted_pct": "Ever submitted (%)",
        "n_unknown_pcd_passed": "UNKNOWN with past primary completion",
        "n_missing_pcd": "Missing primary-completion date",
    }
    rows = [
        {
            "Characteristic": label,
            **{strata[r["stratum"]]: d1(r[key]) if key.endswith("pct") else r[key] for r in trial},
        }
        for key, label in characteristics.items()
    ]
    reporting = [
        {
            "Outcome": "Within 12 months" if r["outcome"] == "within12" else "Ever submitted",
            "Comparison": r["spec"]
            .replace("post minus pre_early", "Post minus early")
            .replace("post minus pre_legacy", "Post minus legacy"),
            "Difference (95% CI)": ci(r),
            "Trials, n": r["n"],
        }
        for r in csvrows(A / "sensitivity/reporting_trial_estimates.csv")
        if r["spec"].startswith("post minus")
    ]
    parts.append(
        "## S11 Table. Trial-level reporting\n\n"
        "The reported outcome is trial-level first results submission within twelve months of primary completion. "
        "Due trials were COMPLETED or TERMINATED with positive ACTUAL enrollment, with primary completion at "
        "least twelve calendar months before September 27, 2026. "
        "Month-only dates use the first day. Primary-completion ACTUAL/ESTIMATED type was not retrieved and "
        "was not imposed. "
        "UNKNOWN trials with past completion dates are reported separately and excluded from due denominators. "
        "Each eligible trial appears once, with no duplicates across awardees or strata. Both trial metrics "
        "use first results submission, not public posting after quality control. "
        "Ever submission includes reports after twelve months and remains subject to unequal follow-up. "
        "All intervals use institution resampling.\n\n" + md(rows) + "\n" + md(reporting)
    )
    rows = [
        {
            "Mechanism": r["mechanism"],
            "Horizon": "Five years" if r["outcome"] in ("primary", "new_5y_registered") else "Seven years",
            "Registration rule": "First submitted by horizon"
            if r["outcome"].endswith("registered")
            else "Any registration by retrieval",
            "New-trial DID (95% CI)": ci(r),
            "Pre / post, n": f"{r['n_pre']} / {r['n_post']}",
        }
        for r in csvrows(A / "sensitivity/registration_horizon_estimates.csv")
        if r["mechanism"] == "K23" and r["outcome"].endswith("registered")
    ]
    parts.append(
        "## S12 Table. Registration by the follow-up horizon\n\n"
        "Both horizons use the same complete-seven-year K23 sample. "
        "Symmetric registration requires first submission no later than K start plus the respective horizon. "
        "Five-year outcomes are nested within seven-year outcomes, with paired institution draws and "
        "fiscal-year and institute adjustment. "
        "The rule excludes retrospective registrations after each horizon but cannot recover "
        "never-registered or unretrieved trials. "
        "Human leadership validation covers five years only.\n\n" + md(rows)
    )
    text = "\n".join(parts).replace("informative_strict", "larger_trial_strict")
    for a, b in (
        ("historical hazard DID", "historical hazard DID"),
        ("historical placebo DID", "historical placebo DID"),
        ("historical E3 FY2018", "FY2018 same-year contrast"),
        ("historical DID", "historical DID"),
        ("| main RD |", "| contemporaneous RD |"),
        ("| historical |", "| historical |"),
        ("| main |", "| contemporaneous |"),
    ):
        text = text.replace(a, b)
    text = re.sub(" ?\\(`[^()]*\\)", "", text)
    text = text.replace(
        "pre-policy limited to 2018-19 legacy-FOA awards (submitted after NOT-OD-16-149)",
        "pre-policy limited to 2018-19 legacy-FOA award starts (application dates unverified)",
    )
    text = text.replace(
        "Pre-policy limited to applications submitted after NOT-OD-16-149",
        "Pre-policy limited to 2018-2019 legacy award starts (application dates unverified)",
    )
    text = re.sub("eTable (\\d+)", "S\\1 Table", text)
    text = re.sub("eFigure (\\d+)\\.", "S\\1 Fig.", text)
    text = text.replace("eMethods 1.", "Methods.")
    text = reader_tables(text)
    # Keep punctuation in data cells intact while removing semicolon connectors from prose.
    text = "\n".join(
        line.replace("; ", ", ") if line.startswith("|") else line.replace("; ", ". ") for line in text.splitlines()
    )
    text = "\n".join(line.rstrip() for line in text.splitlines()) + "\n"
    (ROOT / "figures" / "output" / "supplement.md").write_text(text)


if __name__ == "__main__":
    main()
    print("Supplement: 12 tables; validation 18 cells / 280 sampled / 1847 population")
