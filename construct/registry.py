"""Retrieve symmetric name, grant and institution registry candidates."""

import argparse
import json
import re
import time
import urllib.parse
import urllib.request
from datetime import UTC, datetime

from config import DATA_DIR
from construct.reporter import dump
from outcomes.names import norm


def leadership(p):
    entries = [
        dict(o, source="overallOfficials") for o in p.get("contactsLocationsModule", {}).get("overallOfficials", [])
    ]
    rp = p.get("sponsorCollaboratorsModule", {}).get("responsibleParty", {})
    if rp.get("type") in ["PRINCIPAL_INVESTIGATOR", "SPONSOR_INVESTIGATOR"] and rp.get("investigatorFullName"):
        entries.append(
            {
                "name": rp["investigatorFullName"],
                "affiliation": rp.get("investigatorAffiliation", ""),
                "role": rp["type"],
                "source": "responsibleParty",
            }
        )
    return entries


def named(r, name, override=""):
    return set(norm(r["first_name"] + " " + r["last_name"]).split()) <= set(norm(name).split()) or bool(
        override and name == override
    )


def matches(r, p):
    names = [o["name"] for o in leadership(p)]
    name = any(set(norm(r["first_name"] + " " + r["last_name"]).split()) <= set(norm(n).split()) for n in names)
    ids = json.dumps(p["identificationModule"])
    grant = r["core_project_num"].lower() in re.sub("[^a-z0-9]", "", ids.lower())
    return name or grant


def name_terms(r):
    first = [x for x in re.split("[\\s()\\-]+", r["first_name"]) if len(x.strip(".")) > 1]
    assert first, "Registry query input lacks required name or institution fields."
    return sorted(set([r["first_name"]] + first))


def serial(r):
    return re.sub("^K\\d\\d", "", r["core_project_num"])


def query(r):
    terms = [f'''("{x}" AND "{r["last_name"]}")''' for x in name_terms(r)]
    words = [
        w
        for w in norm(r["institution"]).split()
        if w
        not in {
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
        }
    ]
    assert words, "Registry query input lacks required name or institution fields."
    terms += [
        f'''"{r["core_project_num"]}"''',
        f'''"{r["project_num"]}"''',
        f'"{serial(r)}"',
        f'''(AREA[OverallOfficialName]("{r["last_name"]}") AND "{max(words, key=len)}")''',
    ]
    return "(" + " OR ".join(terms) + ")"


def candidate(r, p):
    surnames = set(norm(r["last_name"]).split())
    lead = any(surnames <= set(norm(o["name"]).split()) for o in leadership(p))
    grant = serial(r).lower() in re.sub("[^a-z0-9]", "", json.dumps(p["identificationModule"]).lower())
    return lead or grant


def searchable(r):
    if any(len(x.strip(".")) > 1 for x in r["first_name"].replace("-", " ").split()):
        return r
    given = " ".join(w for w in r["name"].split() if w.lower() != r["last_name"].lower())
    return dict(r, first_name=given, name_fallback=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("cohort", choices=("contemporaneous", "historical"))
    args = parser.parse_args()
    key = json.loads((DATA_DIR / args.cohort / "cohort_key_private.json").read_text())
    directory = DATA_DIR / ("contemporaneous/sources" if args.cohort == "contemporaneous" else "registry/historical")
    directory.mkdir(parents=True, exist_ok=True)
    total_kept = 0
    for offset in range(0, len(key), 10):
        people = [searchable(r) for r in key[offset : offset + 10]]
        q = " OR ".join(query(r) for r in people)
        token, page, studies = None, 0, []
        while True:
            path = directory / f"ct_full_{offset}_{page}.json"
            if path.exists():
                saved = json.loads(path.read_text())
                assert saved["query"] == q, "Frozen registry query differs from the requested query"
                response = saved["response"]
            else:
                params = {"query.term": q, "pageSize": 100, "countTotal": "true"}
                if token:
                    params["pageToken"] = token
                url = "https://clinicaltrials.gov/api/v2/studies?" + urllib.parse.urlencode(params)
                time.sleep(1.2)
                response = json.load(urllib.request.urlopen(url, timeout=90))
                dump(
                    path,
                    {
                        "query": q,
                        "url": url,
                        "retrieved_at": datetime.now(UTC).isoformat(),
                        "response": response,
                    },
                )
            if page == 0:
                total = response["totalCount"]
            studies.extend(response["studies"])
            token = response.get("nextPageToken")
            page += 1
            if not token:
                break
        assert len(studies) == total, f"expected {total} studies, got {len(studies)}"
        assert len({s["protocolSection"]["identificationModule"]["nctId"] for s in studies}) == total
        for person in people:
            kept = [s for s in studies if candidate(person, s["protocolSection"])]
            item = {
                "pi_id": person["pi_id"],
                "blind_id": person["blind_id"],
                "query": query(person),
                "batch_query": q,
                "status": "complete",
                "studies": kept,
            }
            if args.cohort == "historical":
                item["name_fallback"] = person.get("name_fallback", False)
            dump(directory / f"ct_person_{person['pi_id']}.json", item)
            total_kept += len(kept)
    print("registry people:", len(key), "candidate pairs:", total_kept)


if __name__ == "__main__":
    main()
