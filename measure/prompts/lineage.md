# Scientific lineage rating

Each row describes a new clinical trial led after an NIH K award. `K_title` and
`K_abstract` describe the award's research, with funding designations masked.
`Ktrial_*` fields describe the trial proposed by the award when one is available;
these fields can be empty. `new_*` fields describe the new trial.

Use only the scientific text in that row to assign one `lineage` category:

- `extension`: the same intervention or approach and the same core question as
  the K study, now larger, at multiple sites, at a later phase, or testing
  efficacy after a pilot.
- `same_approach_new_question`: the same intervention or approach applied to a
  new population, condition, or question.
- `related_topic`: the same clinical area or population with a different
  intervention or approach.
- `unrelated`: no substantive link to the K work.
- `unclear`: the K text is too vague to distinguish the categories.

Do not consult outside sources or seek identities, dates, comparison groups,
funding announcements, grant identifiers, or sponsors. Do not undo redactions.

Return one row per input item, preserving the item identifier. Output columns:
`item,lineage,reason`. The reason is one sentence of at most 200 characters naming
the decisive overlap or difference. Every input item must occur exactly once;
use only the five categories above.
