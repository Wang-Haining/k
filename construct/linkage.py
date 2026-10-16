"""Deterministic candidate identity and inclusive date-window rules."""

import json
import re

from construct.registry import leadership, name_terms, serial
from outcomes.dates import interval
from outcomes.names import norm


def followup_window(start, end, value):
    if not value:
        return "missing"
    lo, hi = interval(value)
    if start <= lo and hi <= end:
        return "inside"
    if hi < start:
        return "pre_K"
    if lo > end:
        return "after_5y"
    return "boundary_uncertain"


def linkage_screen(r, p, publication_lead=False):
    ids = re.sub("[^a-z0-9]", "", json.dumps(p["identificationModule"]).lower())
    if serial(r).lower() in ids:
        return "index_grant_lead"
    if publication_lead:
        return "publication_lead"
    surnames = set(norm(r["last_name"]).split())
    given = {w for s in name_terms(r) for w in norm(s).split() if len(w) > 1}
    initials = {w[0] for w in given}
    generic = {
        "university",
        "college",
        "medicine",
        "medical",
        "school",
        "hospital",
        "institute",
        "research",
        "center",
        "of",
        "the",
        "at",
        "and",
        "for",
        "inc",
        "health",
        "system",
        "national",
        "state",
        "department",
    }
    inst = {w for w in norm(r["institution"]).split() if w not in generic and len(w) >= 4}
    acronym = "".join(w[0] for w in norm(r["institution"]).split() if w not in {"of", "the", "at", "and", "for"})
    for o in leadership(p):
        words = norm(o["name"]).split()
        tokens = set(words)
        if not surnames <= tokens:
            continue
        names = [
            w for w in words if w not in surnames and w not in {"dr", "prof", "md", "phd", "mph", "ms", "rn", "mbbs"}
        ]
        if given & tokens or any(w in initials for w in names):
            return "plausible_given_name_and_surname"
        aff = set(norm(o.get("affiliation", "")).split())
        if inst & aff or (len(acronym) > 2 and acronym in aff):
            return "surname_and_institution_lead"
    return "retrieved_surname_only_without_person_or_project_support"


def window(r, date):
    if not date:
        return "missing"
    lo, hi = interval(date)
    if r["start_date"] < lo and hi <= r["end_5y"]:
        return "inside"
    if hi <= r["start_date"]:
        return "pre_K"
    if lo > r["end_5y"]:
        return "after_5y"
    return "boundary_uncertain"
