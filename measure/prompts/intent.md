You read one NIH K08/K23 career-development project abstract. Classify what the awardee's own K research plan proposes. Funding-designation words have been redacted; do not guess the award type. Use only the abstract.

## research_type
- `own_trial_planned`: the K research plan includes a prospective interventional study in humans that the awardee will conduct or lead, in which participants are assigned to an intervention (drug, device, procedure, behavioural, digital, health-services or care-delivery intervention) and outcomes are measured. Pilot, feasibility, single-arm and randomized designs all count, whether the trial is the main aim or one aim. A plan to *design* or *prepare* a future trial without running one during the K does not count.
- `mentor_led_trial_explicit`: the awardee works within an intervention trial that the abstract explicitly says is led or run by a mentor, a parent study or another team, and the awardee does not run their own interventional study.
- `other_research`: no awardee-run prospective interventional study. Examples: observational cohorts, secondary data or EHR analyses, laboratory or animal work, imaging or biomarker studies without an assigned intervention, qualitative work, instrument or model development, and trial-preparation work only.
- `unclear`: the abstract does not let you decide.

## human_intervention_scope
Scope of the awardee-run interventional study, if any:
- `applied`: tests a way to prevent, diagnose, treat or manage a health condition, or to improve care.
- `BESH_only`: the assigned manipulation is only a probe or challenge used to study basic biology or behaviour.
- `none`: no awardee-run interventional study.
- `unclear`.

## evidence
Copy the most decisive phrase from the abstract (at most 200 characters), and give a reason of at most 30 words.
