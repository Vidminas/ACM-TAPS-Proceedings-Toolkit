"""
End-to-end tests of the CHIIR pipeline on the synthetic EasyChair exports in
tests/fixtures (see make_fixtures.py for what each paper exercises).
"""

import csv
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent / "fixtures"))

from make_fixtures import write_fixtures  # noqa: E402
from proceedings import (  # noqa: E402
    ConferenceConfig,
    affiliation_detail_problems,
    check_erights_csv,
    check_xml_against_source,
    export_to_erights_csv,
    export_to_xml,
    heading_previews,
    load_easychair_data,
)

CONFIG = ConferenceConfig.from_json(Path(__file__).parent / "fixtures" / "chiir2027.json")


@pytest.fixture(scope="module")
def files(tmp_path_factory):
    return write_fixtures(tmp_path_factory.mktemp("easychair"))


@pytest.fixture(scope="module")
def xlsx_export(files):
    return load_easychair_data(files["xlsx"], CONFIG)


@pytest.fixture(scope="module")
def csv_export(files):
    return load_easychair_data((files["submission_csv"], files["author_csv"]), CONFIG)


def papers(export):
    return {p.submission_id: p for t in export.tracks for p in t.papers}


def issues(export, category):
    return [i for i in export.validation_issues if i.category == category]


def test_excel_and_csv_inputs_give_identical_models(xlsx_export, csv_export):
    assert xlsx_export.model_dump() == csv_export.model_dump()


def test_decisions_and_categories(xlsx_export):
    by_id = papers(xlsx_export)
    assert set(by_id) == {1, 2, 3, 4, 7, 8}  # 5 rejected, 6 uncategorised
    assert {pid: p.paper_type for pid, p in by_id.items()} == {
        1: "Full Paper", 2: "Short Paper", 3: "Demonstration Paper",
        4: "Doctoral Consortium", 7: "Full Paper", 8: "Tutorial",
    }
    assert [t.section_name for t in xlsx_export.tracks] == [
        "Full Paper", "Short Paper", "Demonstration Paper", "Doctoral Consortium", "Tutorial",
    ]
    assert xlsx_export.decision_counts == {"accept": 6, "probably accept": 1, "reject": 1}
    assert [i.paper_id for i in issues(xlsx_export, "uncategorised")] == [6]
    assert by_id[1].event_tracking_number == "fp1"
    assert by_id[3].event_tracking_number == "dp3"


def test_author_order_comes_from_submissions(xlsx_export):
    paper = papers(xlsx_export)[1]
    assert [a.full_name for a in paper.authors] == ["Ada Lovelace", "Bram Visser", "Chen Wei"]


def test_first_marked_corresponding_author_is_contact(xlsx_export):
    paper = papers(xlsx_export)[1]
    assert [a.full_name for a in paper.corresponding_authors] == ["Bram Visser"]
    flagged = issues(xlsx_export, "multiple_corresponding")
    assert [i.paper_id for i in flagged] == [1]
    assert "Bram Visser" in flagged[0].message


def test_no_corresponding_falls_back_to_first_author(xlsx_export):
    paper = papers(xlsx_export)[3]
    assert [a.full_name for a in paper.corresponding_authors] == ["Eli Novak"]


def test_address_style_affiliation_is_flagged(xlsx_export):
    flagged = issues(xlsx_export, "affiliation_too_detailed")
    assert [(i.paper_id, i.author_name) for i in flagged] == [(2, "Dana Scully")]


@pytest.mark.parametrize("affiliation", [
    "University of California, Berkeley",
    "Max Planck Institute for Informatics, Saarbrücken",
    "Université Paris 8",
    "Microsoft Research",
])
def test_ordinary_affiliations_are_not_flagged(affiliation):
    assert affiliation_detail_problems(affiliation, "France") == []


def test_blank_affiliation_filled_from_other_paper_and_non_ascii(xlsx_export):
    paper = papers(xlsx_export)[7]
    assert paper.authors[0].full_name == "Zoë Ångström"
    assert paper.authors[1].affiliation == "University of Example"
    # Different affiliation on another paper is kept, not overwritten
    assert papers(xlsx_export)[8].authors[0].affiliation == "Example Analytical Engines Ltd"


def test_erights_csv(xlsx_export, tmp_path):
    written = export_to_erights_csv(xlsx_export, tmp_path, "1234567", CONFIG)
    assert written["Full Paper"].name == "CHIIR-2027-Full-Papers.csv"
    for path in written.values():
        assert check_erights_csv(path) == []
    with open(written["All"], encoding="utf-8", newline="") as f:
        rows = list(csv.reader(f))
    assert all(len(r) == 36 for r in rows)
    paper1 = [r for r in rows if r[1] == "fp1"]
    assert [(r[5], r[7], r[9], r[10]) for r in paper1] == [
        ("Ada", "Lovelace", "1", "N"),
        ("Bram", "Visser", "2", "Y"),
        ("Chen", "Wei", "3", "N"),
    ]
    assert paper1[0][0] == "1234567" and paper1[0][2] == "Full Paper"


def test_erights_csv_requires_event_id(xlsx_export, tmp_path):
    with pytest.raises(ValueError):
        export_to_erights_csv(xlsx_export, tmp_path, "", CONFIG)


def test_xml_crosscheck_passes(files, xlsx_export, tmp_path):
    out = tmp_path / "out.xml"
    export_to_xml(xlsx_export, str(out))
    assert check_xml_against_source(files["xlsx"], CONFIG, out) == []
    pair = (files["submission_csv"], files["author_csv"])
    assert check_xml_against_source(pair, CONFIG, out) == []


def test_xml_crosscheck_catches_wrong_order(files, xlsx_export, tmp_path):
    out = tmp_path / "bad.xml"
    export_to_xml(xlsx_export, str(out))
    text = out.read_text(encoding="utf-8")
    out.write_text(text.replace("<first_name>Ada</first_name>", "<first_name>Adah</first_name>", 1),
                   encoding="utf-8")
    assert any("author order" in p for p in check_xml_against_source(files["xlsx"], CONFIG, out))


def test_reissue_single_paper(files, tmp_path):
    export = load_easychair_data(files["xlsx"], CONFIG, paper_id_filter=2)
    assert list(papers(export)) == [2]
    out = tmp_path / "reissue.xml"
    export_to_xml(export, str(out))
    assert check_xml_against_source(files["xlsx"], CONFIG, out, paper_ids=[2]) == []


def test_heading_preview_marks_contact(xlsx_export):
    preview = {p["paper_id"]: p for p in heading_previews(xlsx_export)}["1"]
    assert preview["contact_email"] == "bram@example.nl"
    assert "Bram Visser   ← contact author" in preview["text"]


def test_table_of_contents(files, tmp_path):
    from generate_toc import generate_toc

    toc_text, toc = generate_toc(str(files["taps_xlsx"]), str(tmp_path / "toc"))
    assert list(toc["Title"]) == [
        "Searching Together: Collaborative Query Formulation",
        "Perspectives on Interactive IR",
        "Short Notes on Relevance",
    ]
    assert list(toc["Start Page"]) == [1, 13, 24]
    assert toc["Authors"][1] == "Zoë Ångström and Ada Lovelace"
    assert "FULL PAPER" in toc_text


def test_referees_scan_and_docx(tmp_path):
    import pandas as pd
    from docx import Document

    import referees_to_docx
    import scan_referees

    ref_dir = tmp_path / "referees"
    ref_dir.mkdir()
    pd.DataFrame([
        {"First name": "kim", "Last name": "LEE", "Email": "kim@example.org",
         "Affiliation": "Example University ", "Role": "PC member"},
        {"First name": "Ola", "Last name": "Nordmann", "Email": "ola@example.no",
         "Affiliation": "Eksempel Universitet", "Role": "Senior PC member"},
    ]).to_excel(ref_dir / "full_papers.xlsx", index=False)
    pd.DataFrame([
        {"First name": "Kim", "Last name": "Lee", "Email": "kim@example.org",
         "Affiliation": "Example University", "Role": "PC member"},
    ]).to_excel(ref_dir / "short_papers.xlsx", index=False)

    merged = tmp_path / "referees.xlsx"
    scan_referees.configure(
        file_tracks={"full_papers.xlsx": ["Full Papers", None], "short_papers.xlsx": ["Short Papers", None]},
        track_order=["Full Papers", "Short Papers"],
    )
    try:
        assert scan_referees.main(["--input", str(ref_dir), "--output", str(merged)]) == 0
    finally:
        scan_referees.configure()
    assert pd.ExcelFile(merged).sheet_names == ["Full Papers - SPC", "Full Papers - PC", "Short Papers - PC"]

    out = tmp_path / "committee.docx"
    referees_to_docx.main([
        "--input", str(merged),
        "--section", "Full Papers - SPC=Senior Program Committee:",
        "--section", "Full Papers - PC=Program Committee:",
        "--output", str(out),
    ])
    text = [p.text for p in Document(out).paragraphs if p.text]
    assert text[0] == "Senior Program Committee:    Ola Nordmann (Eksempel Universitet)"
    assert text[1] == "Program Committee:    Kim Lee (Example University)"


def test_runbook_notebook_is_clean_and_compiles():
    import nbformat

    nb = nbformat.read(Path(__file__).parent.parent / "chiir2027_proceedings.ipynb", as_version=4)
    code_cells = [c for c in nb.cells if c.cell_type == "code"]
    assert code_cells
    for cell in code_cells:
        assert not cell.get("outputs"), "Notebook outputs may contain author data; strip them before committing"
        compile(cell.source, "<notebook cell>", "exec")
