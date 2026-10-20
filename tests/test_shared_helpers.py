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
