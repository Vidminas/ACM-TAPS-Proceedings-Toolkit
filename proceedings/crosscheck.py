"""
Output cross-checks
===================

Independent checks of a generated file against the raw EasyChair export,
run after every export. They catch problems in the conversion itself, as
opposed to the data-quality issues reported by the loader.

- check_xml_against_source: right set of papers, author order matches
  Submissions.Authors, institutions/countries match the Authors rows,
  exactly one contact author per paper.
- check_erights_csv: every row has 36 columns and every paper has exactly
  one corresponding author.

Each returns a list of problem strings (empty means the check passed).
"""

import csv
import re
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional

from .config import ConferenceConfig
from .exporters import ERIGHTS_CSV_COLUMNS, clean_affiliation_string
from .loader import Source, accepted_submissions, clean_text, read_easychair


def _norm(name: str) -> str:
    return " ".join(str(name).lower().split())


def names_in_order(names: List[str], authors_str: str) -> bool:
    """
    True if each name occurs in the Submissions.Authors text after the
    previous one. Searching the text, rather than splitting it on commas,
    keeps names that contain a comma (e.g. 'Martin King, Jr.') intact.
    """
    text = _norm(authors_str)
    position = 0
    for name in names:
        found = text.find(name, position)
        if found < 0:
            return False
        position = found + len(name)
    return True


def check_xml_against_source(
    source: Source,
    config: ConferenceConfig,
    xml_file,
    paper_ids=None,
    affiliation_mapping: Optional[Dict[str, str]] = None,
) -> List[str]:
    """
    Compare an ACM XML file with the EasyChair export it was made from.

    Args:
        paper_ids: restrict the expected set (e.g. a single re-issued paper)
        affiliation_mapping: the same mapping passed to the loader, if any
    """
    mapping = affiliation_mapping or {}
    submissions_df, authors_df = read_easychair(source)
    accepted = accepted_submissions(submissions_df, config)
    accepted = accepted[accepted.apply(lambda row: config.categorize(row) is not None, axis=1)]
    if paper_ids is not None:
        accepted = accepted[accepted["#"].isin(set(paper_ids))]
    expected = {int(row["#"]): row for _, row in accepted.iterrows()}

    problems: List[str] = []
    found = set()
    for paper in ET.parse(xml_file).getroot().findall("paper"):
        tracking = paper.findtext("event_tracking_number", "")
        digits = re.findall(r"\d+", tracking)
        if not digits:
            problems.append(f"Paper '{paper.findtext('paper_title', '')}': no numeric event tracking number")
            continue
        paper_id = int(digits[-1])
        found.add(paper_id)
        if paper_id not in expected:
            problems.append(f"Paper #{paper_id}: in XML but not an accepted, categorised submission")
            continue

        xml_authors = paper.findall("authors/author")
        names = [_norm(f"{a.findtext('first_name', '')} {a.findtext('last_name', '')}") for a in xml_authors]

        contacts = [a for a in xml_authors if a.findtext("contact_author", "") == "Y"]
        if len(contacts) != 1:
            problems.append(f"Paper #{paper_id}: {len(contacts)} contact authors (expected exactly 1)")

        authors_str = expected[paper_id].get("Authors", "")
        if isinstance(authors_str, str) and authors_str.strip() and not names_in_order(names, authors_str):
            problems.append(
                f"Paper #{paper_id}: author order {names} does not match Submissions.Authors '{clean_text(authors_str)}'"
            )

        rows = authors_df[authors_df["Submission #"] == paper_id]
        raw = {_norm(f"{clean_text(r['First name'])} {clean_text(r['Last name'])}"): r for _, r in rows.iterrows()}
        if len(rows) != len(xml_authors):
            problems.append(f"Paper #{paper_id}: {len(xml_authors)} authors in XML, {len(rows)} in EasyChair")
        for name, author in zip(names, xml_authors):
            row = raw.get(name)
            if row is None:
                continue
            raw_affiliation = clean_text(row.get("Affiliation", ""))
            raw_affiliation = mapping.get(raw_affiliation.lower(), raw_affiliation)
            raw_institution = clean_affiliation_string(raw_affiliation)
            institution = author.findtext("affiliations/affiliation/institution", "")
            # Empty source values may legitimately be filled from the same author's other papers
            if raw_institution and institution != raw_institution:
                problems.append(
                    f"Paper #{paper_id}, {name}: institution '{institution}' != EasyChair '{raw_institution}'"
                )
            raw_country = clean_text(row.get("Country", ""))
            country = author.findtext("affiliations/affiliation/country", "")
            if raw_country and country != raw_country:
                problems.append(f"Paper #{paper_id}, {name}: country '{country}' != EasyChair '{raw_country}'")

    for paper_id in sorted(set(expected) - found):
        problems.append(f"Paper #{paper_id}: accepted and categorised but missing from XML")
    return problems


def check_erights_csv(csv_file) -> List[str]:
    """Check column count and exactly one corresponding author per paper."""
    problems: List[str] = []
    contacts = defaultdict(int)
    with open(Path(csv_file), encoding="utf-8", newline="") as f:
        for line_no, row in enumerate(csv.reader(f), start=1):
            if len(row) != ERIGHTS_CSV_COLUMNS:
                problems.append(f"{Path(csv_file).name} line {line_no}: {len(row)} columns (expected {ERIGHTS_CSV_COLUMNS})")
                continue
            contacts[row[1]] += row[10] == "Y"
    for paper_id, count in contacts.items():
        if count != 1:
            problems.append(f"{Path(csv_file).name}: paper {paper_id} has {count} corresponding authors (expected 1)")
    return problems
