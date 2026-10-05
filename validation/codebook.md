# Rater codebook


# README: read this first

Rate each item on your own. Do not compare answers or discuss an item with the other rater. The author will resolve disagreements after both files are returned. An agreed answer will remain the reference answer.

Use the information supplied in the workbook. For registry checks, use **ClinicalTrials.gov only: the current record and History of Changes**. Read earlier versions when the current record does not settle the person's role. Do not open NIH RePORTER, award notices, external publications, or general web searches. Do not seek separate protocol documents. Do not try to infer the award's timing, comparison group, or funding announcement. Use the visible K dates only to check the trial-start window. Do not undo redactions.


Keep the sheet names, item codes, row order, and supplied information unchanged. Fill only yellow answer cells. Use the exact drop-down values. Do not add rows. After the pilot, fill every categorical answer. Use `unclear` when evidence cannot settle a judgment; do not guess. Exceptions and limits for each sheet are below. Free-text notes may be blank when there is nothing to add.



# dossier_awardees: one summary per awardee

Read the K title and masked abstract. Use the `item` code to find all matching rows in dossier_trials. Complete those trial rows first. Then run the fresh search below and return to this sheet. An empty candidate list does **not** mean there is no qualifying trial.

For this endpoint, a qualifying trial must meet **all** these conditions:

1. The awardee is the same person named in the registry.
2. The awardee has one of three registry roles: `overall_PI`, `responsible_party_PI`, or `sponsor_investigator`.
3. The study is interventional and its scope is `applied`.
4. Its start date is from `K_start` through `window_end_5y`, including both dates.
5. Its K relationship is established as described below.

| Answer field | Enter `yes` when | Enter `no` or `unclear` when |
|---|---|---|
| `led_K_trial` | At least one qualifying trial is `original_K`. | `no`: all listed trials and the fresh search are resolved, with none qualifying as a K trial. `unclear`: unresolved evidence could change the answer. |
| `led_new_trial` | At least one qualifying trial is `new_protocol`, with no trial-supporting K-grant link. | Apply the same rule for `no` and `unclear` to new trials. |

Both answers can be `yes`: the person may lead a K trial and a separate new trial. A known qualifying trial establishes `yes` even if another candidate remains uncertain. A protocol-only PI does not establish either endpoint under the paper's registry-role definition.

**Example:** the person is registry PI of an applied K pilot starting inside the window, and later leads a separate applied trial inside the window. Code `yes` for both fields if the second trial is distinct and not supported by the K grant.

## Mandatory fresh name search

Do this for **every awardee**, including people with listed trials and people with no listed trials.

1. Open `ctgov_name_search`, or search the person's full name in the ClinicalTrials.gov search box. Do not restrict recruitment status or search dates.
2. Repeat with given name plus surname, middle initial or full middle name when supplied, and first initial plus surname. For compound or hyphenated surnames, try the supplied parts and spacing variants. Try a documented alternate name or plausible one-letter spelling variant. Do not assume that a similar name identifies the same person.
3. If the name is common, search surname plus the supplied institution. Check affiliations and the scientific topic. Do not use institution alone to exclude a plausible move.
4. Open plausible records. Check Contacts and Locations, Sponsor/Collaborators, identifiers, study type, start date, and History of Changes. Apply the same identity, role, scope, window, and K-relationship rules as for listed trials.
5. Compare each NCT number with this awardee's dossier_trials rows. Record each **additional confirmed qualifying trial** once in `missed_trials_found`. Include the NCT number and a one-line reason. Include its K/new classification and decisive registry evidence. Use one line per NCT.

Format example, using a fictional identifier: `NCT followed by eight digits — new_protocol; same person and registry PI; applied interventional study; start 2020-04-15 is inside the window; distinct question and no K support link.`

Do not put already listed trials, out-of-window trials, or nonqualifying roles in `missed_trials_found`. Put a plausible but unresolved additional trial in `notes`, and use `unclear` for an affected leadership answer unless another trial already establishes `yes`. A trial absent from the workbook is a candidate retrieval miss; it may have been omitted by the 30-trial display cap. It is not automatically an awardee-level false negative.

Leave `missed_trials_found` **blank only when you found no additional confirmed qualifying trial**. Set `search_done` to `yes` after completing the search and checking plausible hits. Use `no` for an unfinished search, or `unclear` if access or missing evidence prevents completion. Explain these in `notes`. A final `no` leadership answer requires a completed search. List the name variants used in `notes`.

\newpage

# dossier_trials: judge each listed trial

Use the awardee's dossier_awardees row for the name, institution, K plan, and date window. The listed trial information is a starting point. Check the current registry and, when needed, History of Changes. Record the decisive source in `evidence`.

## identity

| Value | Meaning |
|---|---|
| `same_person` | The name matches. Also, at least one is true: the affiliation matches a supplied institution; a plausible move has clear topic continuity; or the K number appears in the record. |
| `different_person` | The surname and given name or initial match, but affiliation, country, or discipline clearly identifies someone else. |
| `not_named` | No connected person has the surname together with the given name or first initial. A surname alone is insufficient. |
| `unclear` | The available evidence does not settle identity. |

Read surname-first names carefully. A mismatched given name is not a match merely because the surname appears. Check nicknames and one-letter variants against affiliation evidence; note the variant. Nickname matches require affiliation evidence; the instrument name guard may not accept them. A name in a reference list alone is `not_named`. A registry username alone is `unclear` unless the record resolves it.

## role

If identity is `not_named` or `different_person`, use `not_named` for role. Otherwise, choose the first applicable role in this order:

| Value | Meaning |
|---|---|
| `overall_PI` | Overall Officials names this person as Principal Investigator, in the current record or an earlier version. |
| `responsible_party_PI` | Responsible Party names this person and has type Principal Investigator. |
| `sponsor_investigator` | Responsible Party names this person and has type Sponsor-Investigator. |
| `protocol_named_PI` | An explicitly available protocol excerpt identifies the person as this study's PI or an overall PI. This descriptive answer remains available, but does not qualify for the paper's registry leadership endpoint. Do not seek separate documents. |
| `nonqualifying_role` | Only Study Director, Study Chair, site/local PI, co-investigator, contact, author, corresponding author, funding-grant PI, or a bare name in a list. |
| `unclear` | The person is named, but the role cannot be determined. |

An earlier registry version that names the person as PI counts. Do not require the person to be PI in the first version. The execution panel studies initial versus later responsibility separately; that distinction does not change this leadership endpoint. A site PI on a multicentre trial is not an overall PI.

\newpage

## scope

Ask: **Is the assigned intervention tested to prevent, diagnose, treat, or manage a health condition, or improve care?**

| Value | Meaning and example |
|---|---|
| `applied` | Yes. Includes pilot, feasibility, behavioural, health-services, and care-delivery trials. A study of how a therapy works can count, including in healthy volunteers. Example: assigned counselling to improve medication adherence. |
| `BESH_only` | The assigned manipulation is only a probe of biology or behaviour, even in patients. Examples: a test meal, fasting challenge, substance challenge, stimulation, stress task, or mood induction used only to study a mechanism. |
| `no_human_intervention` | Nothing is assigned, or the assigned procedure only measures something and does not guide care. Includes observational or animal work, imaging, biomarker collection, questionnaires, and measurement-device validation. |
| `unclear` | The purpose or assignment cannot be established. |

The registry's `BASIC_SCIENCE` purpose does not decide scope by itself. Judge the therapy-versus-probe purpose. An observational study does not qualify even if it studies an effective treatment.

## start_in_window

Use the **study start date**, not registration, submission, completion, or publication dates. Compare it with the supplied `K_start` and `window_end_5y`.

- `yes`: the start is on or after K start and on or before the window end.
- `no`: the start is before K start or after the window end.
- `unclear`: the date is missing, contradictory, or not precise enough to decide.

For a partial date, use its possible range. A month fully inside the window is `yes`. A month fully outside is `no`. A month that crosses a boundary is `unclear`. Do not invent a day. Example: with K start 2018-07-15, a trial start recorded only as July 2018 is `unclear`; 2018-07-15 is `yes`. Do not move the window to include a K trial that began earlier. Withdrawn trials with zero enrolled can still count if all endpoint conditions are met.

## k_relationship

Use the definitions in boundary below. For this field, retain the applicability rule: answer when identity is `same_person` and role is one of the four PI-labelled values, including the descriptive `protocol_named_PI`. Otherwise use `not_applicable`. This field rule does not make a protocol-only PI qualify for the endpoint.

A K number that supports the **trial** makes it `original_K`, even if the scientific question has changed. Personal support wording alone, such as “Dr X is supported by K23…”, does not establish support for the trial. A new trial must be both distinct from the K plan and not linked to the K grant as trial support.

## evidence

Copy the decisive phrase, up to 200 characters, and name the source. For history, include the version date. Example: `History, 2021-03-02, Overall Officials: “Alex Lee, Principal Investigator”. Start 2019-06-01; same pilot as K aim 2.` dossier_trials has no separate `role_source` column; put the source here.

\newpage

# intent: classify the K plan

Use **only the supplied masked abstract**. Do not search for another version. Choose one `intent` value. The four definitions below are reproduced verbatim from `measure/prompts/intent.md`:

- `own_trial_planned`: the K research plan includes a prospective interventional study in humans that the awardee will conduct or lead, in which participants are assigned to an intervention (drug, device, procedure, behavioural, digital, health-services or care-delivery intervention) and outcomes are measured. Pilot, feasibility, single-arm and randomized designs all count, whether the trial is the main aim or one aim. A plan to *design* or *prepare* a future trial without running one during the K does not count.
- `mentor_led_trial_explicit`: the awardee works within an intervention trial that the abstract explicitly says is led or run by a mentor, a parent study or another team, and the awardee does not run their own interventional study.
- `other_research`: no awardee-run prospective interventional study. Examples: observational cohorts, secondary data or EHR analyses, laboratory or animal work, imaging or biomarker studies without an assigned intervention, qualitative work, instrument or model development, and trial-preparation work only.
- `unclear`: the abstract does not let you decide.

Examples: “We will enrol 20 patients and assign the intervention in aim 2” can be `own_trial_planned`. “I will analyse data from my mentor's trial” is `mentor_led_trial_explicit` when leadership by the mentor is explicit. “We will develop a protocol for a future trial” is `other_research`. Do not infer mentor leadership just because a mentor is mentioned.

In `reason`, copy the decisive phrase, up to 200 characters, followed by a reason of up to 30 words. This workbook has no `human_intervention_scope` field for intent; do not add one. The binary intent endpoint is `own_trial_planned` versus the two clear alternatives. `unclear` remains unresolved.

# boundary: distinguish the K study from a new protocol

Use the supplied K title/abstract and trial scientific fields. This sheet deliberately omits identifiers and dates. Do not search to recover them. Identity, role, and timing are not questions on this sheet.

| `k_relationship` | Definition |
|---|---|
| `original_K` | The study proposed in the K abstract: the same intervention, population, **and** primary question. Also includes an explicitly described component of the K aims, such as the K's own pilot or feasibility trial. In modules where support identifiers are visible, a K grant supporting the trial also establishes this category. |
| `new_protocol` | A distinct trial with a different intervention, population, or primary question. Includes a follow-on trial of the K intervention with new funding, such as an R01 or a multi-site trial, and a companion trial with a different primary question. It must not be supported by the K grant. |
| `unclear` | The K abstract or trial description is too vague to decide. |

Example: the K proposes a 20-person counselling pilot and the record describes that pilot: `original_K`. A separate later efficacy protocol that builds on the pilot can be `new_protocol`. A larger sample alone does not prove that it is a separate protocol; it may be the same K study. Judge the study described, not the shared disease name.

For boundary, judge the scientific relationship from the visible text. Do not infer the presence or absence of withheld grant links. Thus this module audits the scientific K/new judgment, not an independent grant-link check. Record the decisive comparison in `reason`, ideally one short sentence. `not_applicable` is not an allowed boundary answer.

# lineage: how does the new trial relate scientifically to K work?

Use the supplied K text, the K-trial text when available, and the new trial's scientific fields. Do not search for dates, grant identifiers, or sponsors. The question is about scientific continuity in a distinct new trial. It is not a second K/new decision.

| `lineage` | Category | Meaning and example |
|---|---|---|
| `extension` | (i) | Direct extension of the K study: same intervention and question, larger or later phase. Example: a separate efficacy trial extends the K feasibility study. |
| `same_approach_new_question` | (ii) | Same intervention or approach, new population or question. Example: the K counselling approach is tested in a new patient group. |
| `related_topic` | (iii) | Related topic, different intervention. Example: the K studied counselling for diabetes; the new trial tests a different drug for diabetes. |
| `unrelated` | (iv) | No substantive scientific connection to the K work. Example: the K studied diabetes counselling; the new trial studies fracture surgery. |

Apply the most specific supported category: first (i), then (ii), then (iii), then (iv). **(i) and (ii) mean “developed from the K work”.** A new protocol can be an `extension`; scientific continuity does not make two protocols the same study. This judgment does not show when an idea or skill was acquired.

If K-trial fields are empty, compare with the K abstract. Do not assume there was no K work. Give a short `reason` naming the shared or different intervention and question. There is no `unclear` option on this sheet. If the supplied text is insufficient for any defensible category, leave `lineage` blank, explain in `reason`, and return it for clarification before final scoring. Do not use `unrelated` to mean missing evidence.

\newpage
