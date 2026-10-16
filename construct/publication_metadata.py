"""Publication metadata."""

import re
import xml.etree.ElementTree as ET
from difflib import SequenceMatcher

from construct.registry import norm


def load_metadata(raw, wanted, completed_ids):
    metadata = {}
    files = []
    for folder in [raw / "pubmed_exact", raw / "pubmed_prefix", raw]:
        files.extend(
            p
            for p in sorted(folder.glob("pubmed_*.xml"))
            if folder != raw or int(p.name.split("_")[1]) in completed_ids
        )
    for path in files:
        for _event, a in ET.iterparse(path, events=("end",)):
            if a.tag not in {"PubmedArticle", "PubmedBookArticle"}:
                continue
            pmid = a.findtext(".//PMID")
            if pmid in wanted and pmid not in metadata:
                author_list = a.find(".//Article/AuthorList")
                authors = [] if author_list is None else author_list.findall("Author")
                sources = {}

                def ncts(el, location, sources=sources):
                    for value in [el.text, el.tail]:
                        for n in re.findall("NCT\\d{8}", value or ""):
                            sources.setdefault(n, set()).add(location)
                    for child in el:
                        ncts(child, location + "/" + child.tag)

                ncts(a, a.tag)
                dates = [
                    dict(
                        {k: d.findtext(k, "") for k in ["Year", "Month", "Day", "MedlineDate"]},
                        source=source,
                        date_type=d.get("DateType"),
                    )
                    for source, elements in [
                        ("JournalIssue/PubDate", a.findall(".//JournalIssue/PubDate")),
                        ("Article/ArticleDate", a.findall(".//Article/ArticleDate")),
                    ]
                    for d in elements
                ]
                metadata[pmid] = {
                    "xml_source_file": str(path),
                    "author_list_complete": author_list.get("CompleteYN") if author_list is not None else None,
                    "collective_names": [p.findtext("CollectiveName") for p in authors if p.findtext("CollectiveName")],
                    "raw_authors": [
                        (p.findtext("LastName", ""), p.findtext("ForeName", ""), p.findtext("Initials", ""))
                        for p in authors
                    ],
                    "publication_dates": dates,
                    "nct_provenance": [{"nct_id": n, "xml_paths": sorted(v)} for n, v in sorted(sources.items())],
                }
            a.clear()
    assert wanted <= metadata.keys(), "Required source invariant failed; inspect the private input locally."
    print("PUBLICATION XML METADATA", len(metadata), "PMIDs from", len(files), "saved XML files", flush=True)
    return metadata


def institution_phrase(value):
    return " ".join(w for w in norm(re.sub("(?i)\\bUNIV\\b", "university", value)).split() if w not in {"the", "at"})


def affiliation_matches(institution, affiliations):
    phrase = institution_phrase(institution)
    assert phrase, "Required source invariant failed; inspect the private input locally."
    return any(" " + phrase + " " in " " + institution_phrase(a) + " " for a in affiliations)


def orcid(value):
    value = re.sub("^https?://(?:www\\.)?orcid\\.org/", "", (value or "").strip(), flags=re.I).upper().rstrip("/")
    if not re.fullmatch("\\d{4}-\\d{4}-\\d{4}-\\d{3}[\\dX]", value):
        return None
    digits = value.replace("-", "")
    total = 0
    for digit in digits[:-1]:
        total = (total + int(digit)) * 2
    check = (12 - total % 11) % 11
    return value if digits[-1] == ("X" if check == 10 else str(check)) else None


def given_variants(r):
    first = norm(re.sub("\\([^)]*\\)", "", r["first_name"])).split()
    full = norm(re.sub("\\([^)]*\\)", "", r["name"])).split()
    last = norm(r["last_name"]).split()
    assert first and last, "Required source invariant failed; inspect the private input locally."
    canonical = full[: -len(last)] if full[-len(last) :] == last else first
    if canonical[: len(first)] != first:
        canonical = first
    return [canonical] + [norm(v).split() for v in re.findall("\\(([^)]+)\\)", r["first_name"]) if norm(v)]


def name_relation(expected, actual):
    words = norm(actual).split()
    if not words:
        return "incomplete"
    relations = []
    for names in expected:
        pairs = list(zip(names, words, strict=False))
        compatible = all((x == y or ((len(x) == 1 or len(y) == 1) and x[0] == y[0]) for x, y in pairs))
        if compatible:
            relations.append("compatible_expanded" if len(names[0]) > 1 and words[0] == names[0] else "initials_only")
            continue
        x, y = (names[0], words[0])
        nickname = (
            len(x) > 1
            and len(y) > 1
            and (x.startswith(y) or y.startswith(x) or x[:3] == y[:3] or (SequenceMatcher(None, x, y).ratio() >= 0.65))
        )
        middle_conflict = any((a[0] != b[0] for a, b in pairs[1:]))
        first_conflict = len(x) > 1 and len(y) > 1 and (x != y) and (not nickname)
        relations.append(
            "expanded_first_and_middle_conflict" if first_conflict and middle_conflict else "unresolved_name_variant"
        )
    for status in ["compatible_expanded", "initials_only", "unresolved_name_variant"]:
        if status in relations:
            return status
    return "expanded_first_and_middle_conflict"


def author_evidence(r, article, meta):
    expected = given_variants(r)
    evidence = []
    authors = article.get("authors", [])
    if article.get("record_type") == "PubmedBookArticle":
        return evidence
    assert len(authors) == len(meta["raw_authors"]), (
        "Required source invariant failed; inspect the private input locally."
    )
    grant = any(
        re.sub("[^a-z0-9]", "", r["core_project_num"].lower())
        in re.sub("[^a-z0-9]", "", (g.get("GrantID") or "").lower())
        for g in article["grants"]
    )
    for i, p in enumerate(authors):
        assert (p["last"], p["first"]) == meta["raw_authors"][i][:2], (
            "Required source invariant failed; inspect the private input locally."
        )
        if norm(p["last"]) != norm(r["last_name"]):
            continue
        identifiers = [z["value"] for z in p["identifiers"] if (z.get("source") or "").upper() == "ORCID"]
        valid = sorted({orcid(v) for v in identifiers if orcid(v)})
        relation = name_relation(expected, p["first"])
        aff = affiliation_matches(r["institution"], p["affiliations"])
        reason = []
        if relation == "compatible_expanded" and aff:
            reason.append("ordered_name_and_complete_institution_phrase")
        if relation == "compatible_expanded" and grant:
            reason.append("ordered_name_and_index_grant")
        evidence.append(
            {
                "author_index": i,
                "last": p["last"],
                "first": p["first"],
                "raw_initials": meta["raw_authors"][i][2],
                "name_relation": relation,
                "affiliations": p["affiliations"],
                "institution_match": aff,
                "index_grant_match": grant,
                "ORCIDs": valid,
                "invalid_ORCIDs": [v for v in identifiers if not orcid(v)],
                "anchor_reasons": reason,
            }
        )
    return evidence


def identity_status(meta, evidence, anchors):
    matched = [p for p in evidence if set(p["ORCIDs"]) & anchors]
    if any(p["name_relation"] not in {"compatible_expanded", "initials_only"} for p in matched):
        return ("identity_unresolved", "anchored_ORCID_name_conflict")
    if any(p["anchor_reasons"] for p in evidence):
        return ("supported", "name_and_institution_or_index_grant")
    if matched:
        return ("supported", "anchored_target_author_ORCID")
    conflict = (
        meta["author_list_complete"] == "Y"
        and (not meta["collective_names"])
        and evidence
        and all(
            p["name_relation"] == "expanded_first_and_middle_conflict"
            and (not p["institution_match"])
            and (not p["index_grant_match"])
            for p in evidence
        )
    )
    return (
        ("explicit_author_conflict", "complete_list_expanded_first_and_middle_conflict")
        if conflict
        else ("identity_unresolved", "no_sufficient_target_author_identity_evidence")
    )
