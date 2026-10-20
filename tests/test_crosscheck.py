"""Regression tests for proceedings.crosscheck."""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

from proceedings import ConferenceConfig, check_xml_against_source, export_to_xml, load_easychair_data  # noqa: E402
from proceedings.crosscheck import names_in_order  # noqa: E402

CONFIG = ConferenceConfig.from_json(Path(__file__).parent / "fixtures" / "chiir2027.json")


def test_names_in_order():
    assert names_in_order(["ann lee", "martin king, jr.", "bo chen"], "Ann Lee, Martin King, Jr. and Bo Chen")
    assert not names_in_order(["bo chen", "ann lee"], "Ann Lee and Bo Chen")
    assert not names_in_order(["ann lee", "eve stone"], "Ann Lee and Bo Chen")


def test_name_with_comma_passes_crosscheck(tmp_path):
    submissions = pd.DataFrame([{"#": 1, "Track name": "CHIIR 2027 PC", "Title": "T",
                                 "Authors": "Ann Lee, Martin King, Jr. and Bo Chen",
                                 "Form fields": "(Category) Full Paper", "Decision": "accept"}])
    authors = pd.DataFrame([
        {"Submission #": 1, "First name": first, "Last name": last, "Email": email,
         "Affiliation": "U", "Country": "UK", "Corresponding?": "✔" if first == "Ann" else ""}
        for first, last, email in [("Ann", "Lee", "ann@x.org"), ("Bo", "Chen", "bo@x.org"),
                                   ("Martin", "King, Jr.", "mk@x.org")]
    ])
    source = (tmp_path / "submission.csv", tmp_path / "author.csv")
    submissions.to_csv(source[0], index=False)
    authors.to_csv(source[1], index=False)

    export = load_easychair_data(source, CONFIG)
    out = tmp_path / "out.xml"
    export_to_xml(export, str(out))
    assert check_xml_against_source(source, CONFIG, out) == []
