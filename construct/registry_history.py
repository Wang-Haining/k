"""Compact complete registry version captures into the execution-panel schema."""

import json
import re

from config import DATA_DIR
from construct.reporter import dump

STARTED = {"RECRUITING", "ENROLLING_BY_INVITATION", "ACTIVE_NOT_RECRUITING", "COMPLETED"}


def compact(capture, serial):
    """Retain the initial PI/grant state and each subsequent change, using zero-based versions."""
    changes = capture["overview"]["history"]["changes"]
    versions = capture["versions"]
    assert changes and versions, "Expected nonempty registry history"
    expected = {c["version"] for c in changes}
    actual = {v["studyVersion"] for v in versions}
    assert len(actual) == len(versions) and actual == expected, "Incomplete or duplicate registry versions"
    assert min(actual) == 0, f"Expected initial version 0, got {min(actual)}"
    events, recruited = [], False
    for version in sorted(versions, key=lambda v: v["studyVersion"]):
        protocol = version["study"]["protocolSection"]
        names = [
            "O:" + o["name"]
            for o in protocol.get("contactsLocationsModule", {}).get("overallOfficials", [])
            if o.get("role") == "PRINCIPAL_INVESTIGATOR" and o.get("name")
        ]
        responsible = protocol.get("sponsorCollaboratorsModule", {}).get("responsibleParty", {})
        if responsible.get("type") in {"PRINCIPAL_INVESTIGATOR", "SPONSOR_INVESTIGATOR"} and responsible.get(
            "investigatorFullName"
        ):
            names.append("R:" + responsible["investigatorFullName"])
        identification = re.sub("[^a-z0-9]", "", json.dumps(protocol["identificationModule"]).lower())
        linked = int(serial.lower() in identification)
        event = [version["studyVersion"], "", names, linked]
        if not events or event[2:] != events[-1][2:]:
            events.append(event)
        recruited |= protocol.get("statusModule", {}).get("overallStatus") in STARTED
    return {"ev": events, "rec": int(recruited)}


def main():
    roster = json.loads((DATA_DIR / "derived/ktrial_panel_input_private.json").read_text())
    captures = json.loads((DATA_DIR / "sources/registry_history.json").read_text())
    assert roster and len({r["nct"] for r in roster}) == len(roster), "Expected unique nonempty trial roster"
    assert set(captures) == {r["nct"] for r in roster}, "History captures do not match the trial roster"
    output = {r["nct"]: compact(captures[r["nct"]], r["serial"]) for r in roster}
    dump(DATA_DIR / "derived/ktrial_history.json", output)
    print("registry histories:", len(output), "PI/grant states:", sum(len(v["ev"]) for v in output.values()))


if __name__ == "__main__":
    main()
