You review one pair: an NIH K08/K23 career-development awardee and one ClinicalTrials.gov record retrieved because it might involve that awardee. Use only the packet. Do not guess the award type. Answer in the required JSON.

The packet has four parts:
- `awardee`: the person and their K project (title, abstract, K window, NIH organizations they have been funded at).
- `trial`: current registry fields (titles, summary, interventions, design, start date, lead sponsor, responsible party, overall officials, secondary IDs).
- `historical_registry_snapshots`: officials and responsible parties recorded in 2022 or 2024 archive copies of this record.
- `protocol_excerpts`: lines from protocol documents or published protocols that mention the awardee's surname or a leadership role.

## identity
Is the awardee named anywhere in this packet as a person connected to the trial?
- `not_named`: no person in the trial record, snapshots or excerpts carries the awardee's surname together with the awardee's given name or first initial. A person sharing only the surname (different given name and initial) does not count as named. A trial found only through a keyword or grant number, with the awardee not named, is `not_named`.
- `same_person`: a named person is consistent with the awardee, meaning the surname plus the given name or initial match, AND one of these holds:
  - the affiliation is one of the awardee's NIH organizations;
  - the affiliation is a plausible move with clear topical continuity with the K project;
  - the K serial appears in the record.
- `different_person`: a person with the awardee's surname and a matching given name or first initial, whose affiliation, country or discipline is clearly inconsistent with the awardee.
- `unclear`: otherwise. Never guess.

## role
The awardee's role in THIS trial. If identity is `not_named` or `different_person`, the awardee is not in this trial: use `not_named`. If several roles apply, report the first in this order: overall_PI, responsible_party_PI, sponsor_investigator, protocol_named_PI.
- `overall_PI`: listed in overall officials with role PRINCIPAL_INVESTIGATOR (current record or snapshot).
- `responsible_party_PI`: named as the responsible party of type Principal Investigator.
- `sponsor_investigator`: named as the responsible party of type Sponsor-Investigator.
- `protocol_named_PI`: a protocol excerpt contains an explicit statement that the awardee, identified by surname plus given name or initial, is THIS study's Principal Investigator or one of its named overall Principal Investigators (for example "Principal Investigator: Jane Q. Doe"). Authorship, corresponding author, co-investigator, grant PI of the funding award, funding or disclosure lines, a bare name in a list, or "Dr. Doe (PI)" without a given name or initial are NOT protocol_named_PI.
- `nonqualifying_role`: named only as Study Director, Study Chair, site/local PI, sub-investigator, co-investigator, collaborator, contact, author or corresponding author, grant PI of the funding award, or similar.
- `unclear`: named, but the role cannot be determined.

## role_source
Where the qualifying role is documented: `current_registry`, `historical_snapshot`, `protocol_excerpt`, or `none` when the role is not qualifying. If more than one source documents it, prefer current_registry, then historical_snapshot, then protocol_excerpt.

## scope (always)
First ask: is the assigned intervention being evaluated as a potential way to prevent, diagnose, treat or manage a health condition, or to improve care? Then classify.
- `applied`: humans are prospectively assigned an intervention intended to prevent, diagnose, treat, rehabilitate, or improve health, behaviour, or care delivery. This includes mechanistic studies of a therapy, behavioural and health-services interventions, and feasibility or pilot trials.
- `BESH_only`: the assigned thing is only a probe or challenge used to study physiology, biology or behaviour (a test meal, fasting vs fed state, a drug, alcohol or substance challenge, a stimulation or stress task, a mood induction), even when participants have a disease or the registry calls it a drug. A therapy given (including to healthy volunteers) to study how that therapy works is `applied`, not BESH.
- `no_human_intervention`: nothing is prospectively assigned to humans, or the only assigned procedure is a measurement whose results are not used to guide participants' care (imaging, glucose monitoring or tolerance testing, biomarker or specimen collection, questionnaire or device validation). Also observational and animal-only work.
- `unclear`: the packet cannot decide.

## k_relationship
Answer only when identity is `same_person` AND the role is one of the four qualifying roles. Otherwise answer `not_applicable`.
- `original_K`: this trial is the study proposed in the K abstract, meaning the intervention, the population AND the primary question all match; OR it is an explicitly described component of the K aims (including the K's own feasibility or pilot trial of the K intervention); OR the K serial appears anywhere in the packet as a grant supporting this trial (registry IDs, or a protocol funding statement).
- `new_protocol`: a distinct trial, with a different intervention, population or question, that is not one of the K aims as described. A related topic or a shared drug class alone does not make it original_K. A follow-on trial of the K intervention with its own new funding (for example an R01 or multi-site trial), a new population or a new primary question is `new_protocol`; so is a companion study with the same intervention and population but a different primary question.
- `unclear`: the abstract is too vague to decide.
- Do not decide from dates, sponsors or funding alone.

## evidence and reason
- `evidence`: copy the single most decisive short phrase from the packet, at most 200 characters (for example the official entry naming the awardee). Use an empty string if nothing is decisive.
- `reason`: at most 40 words.
