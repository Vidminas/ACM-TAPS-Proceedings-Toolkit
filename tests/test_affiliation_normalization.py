"""
Affiliation cleaning: the exporters strip surrounding whitespace and
leading/trailing punctuation before writing an institution.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from proceedings.text import clean_affiliation_string  # noqa: E402


@pytest.mark.parametrize("raw, expected", [
    ("Kuaishou Technology Co., Ltd.", "Kuaishou Technology Co., Ltd"),
    ("MIT, ", "MIT"),
    (", Stanford University", "Stanford University"),
    (" , Tsinghua University", "Tsinghua University"),
    ("Meta Platforms, Inc.", "Meta Platforms, Inc"),
    ("University of Washington.", "University of Washington"),
    ("..Amazon..", "Amazon"),
    ("Normal University", "Normal University"),
    ("", ""),
    (None, ""),
    ("  Harvard University  ", "Harvard University"),
])
def test_clean_affiliation_string(raw, expected):
    assert clean_affiliation_string(raw) == expected
