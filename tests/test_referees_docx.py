"""Regression tests for referees_to_docx.py."""

import sys
from pathlib import Path

import pandas as pd
from docx import Document

sys.path.insert(0, str(Path(__file__).parent.parent))

from referees_to_docx import write_committee_docx  # noqa: E402


def committee_text(path):
    return [p.text for p in Document(path).paragraphs if p.text]


def test_affiliation_with_parentheses_round_trips(tmp_path):
    rows = pd.DataFrame([
        {"first name": "Li", "middle name": None, "last name": "Wei",
         "affiliation": "Harbin Institute of Technology (Shenzhen)"},
        {"first name": "Robert (Bob)", "middle name": None, "last name": "Smith",
         "affiliation": "Example University"},
    ])
    out = tmp_path / "committee.docx"
    write_committee_docx([("Program Committee:", rows)], str(out))  # raises SystemExit on mismatch
    assert committee_text(out)[0] == "Program Committee:    Li Wei (Harbin Institute of Technology (Shenzhen))"
