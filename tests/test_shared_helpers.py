"""Shared helpers stay single implementations."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import proceedings.exporters  # noqa: E402
import proceedings.validation.checks  # noqa: E402
import proceedings.validation.statistics  # noqa: E402
from proceedings.text import clean_affiliation_string  # noqa: E402


def test_one_clean_affiliation_string():
    for module in (proceedings.exporters, proceedings.validation.checks, proceedings.validation.statistics):
        assert module.clean_affiliation_string is clean_affiliation_string
    assert clean_affiliation_string(None) == ""
    assert clean_affiliation_string(" , Stanford University.") == "Stanford University"


def test_referees_and_papers_read_the_mapping_identically(tmp_path):
    import json

    import scan_referees
    from proceedings.loader import load_affiliation_mapping

    path = tmp_path / "map.json"
    path.write_text(json.dumps({"affiliations": {" Adobe Inc. ": "Adobe", "MIT": "Massachusetts Institute of Technology"}}))
    assert scan_referees.load_mappings(str(path)) == load_affiliation_mapping(path) == {
        "adobe inc.": "Adobe", "mit": "Massachusetts Institute of Technology"}
