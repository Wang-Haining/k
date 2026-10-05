"""Apply the registry query support rule to archived candidates."""

import json

from config import DATA_DIR
from construct.registry import name_terms
from construct.reporter import dump
from outcomes.names import norm


def main():
    folder = DATA_DIR / "contemporaneous"
    path = folder / "archive_candidate_retrieval.json"
    data = json.loads(path.read_text())
    key = {r["pi_id"]: r for r in json.loads((folder / "cohort_key_private.json").read_text())}
    for row in data["new_leads"]:
        person = key[row["pi_id"]]
        given = {w for name in name_terms(person) for w in norm(name).split() if len(w) > 1}
        words = [
            w
            for w in norm(person["institution"]).split()
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
        assert words, "No distinctive institution word"
        word = max(words, key=len)
        evidence = row["archive_evidence"]
        grant = any(e["table"] == "id_information" for e in evidence)
        named = [e["raw"] for e in evidence if e["table"] != "id_information"]
        full = any(given & set(norm(r["name"]).split()) for r in named)
        affiliation = any(word in norm(r.get("affiliation", "")).split() for r in named)
        row["current_query_compatible"] = grant or full or affiliation
    dump(path, data)
    print(
        "archive leads:",
        len(data["new_leads"]),
        "query compatible:",
        sum(r["current_query_compatible"] for r in data["new_leads"]),
    )


if __name__ == "__main__":
    main()
