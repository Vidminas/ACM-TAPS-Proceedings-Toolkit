"""
Pydantic model validation tests: Author, Paper (including the contact-author
priority), ProceedingsExport issue tracking and statistics, and tolerance of
authors with different affiliations or emails across papers.
"""

import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).parent.parent))

from proceedings.models import (  # noqa: E402
    Author,
    Paper,
    ProceedingsExport,
    Track,
    validate_author_name_consistency,
)


def make_paper(authors, submission_id=1, title="Paper"):
    return Paper(submission_id=submission_id, title=title, authors=authors,
                 track_name="Track", section_name="Section", paper_type="Type")


def contact_last_names(paper):
    return [a.last_name for a in paper.corresponding_authors]


# --- Author -----------------------------------------------------------------

def test_valid_author():
    author = Author(first_name="John", last_name="Doe", email="john.doe@example.com",
                    affiliation="University of Example", country="USA")
    assert author.full_name == "John Doe"
    assert author.email == "john.doe@example.com"


def test_empty_first_name_is_rejected():
    with pytest.raises(ValidationError):
        Author(first_name="", last_name="Doe", email="john.doe@example.com")


def test_invalid_email_is_rejected():
    with pytest.raises(ValidationError):
        Author(first_name="John", last_name="Doe", email="not-an-email")


def test_author_with_minimal_fields():
    author = Author(first_name="Jane", last_name="Smith")
    assert author.email is None and author.affiliation is None


# --- Paper ------------------------------------------------------------------

def test_valid_paper():
    paper = make_paper([Author(first_name="John", last_name="Doe", email="john@example.com"),
                        Author(first_name="Jane", last_name="Smith", email="jane@example.com")],
                       submission_id=123, title="A Great Paper")
    assert paper.author_count == 2
    assert paper.title == "A Great Paper"
    assert len(paper.corresponding_authors) == 1


def test_paper_without_authors_is_rejected():
    with pytest.raises(ValidationError):
        make_paper([])


def test_paper_with_empty_title_is_rejected():
    with pytest.raises(ValidationError):
        make_paper([Author(first_name="John", last_name="Doe")], title="")


def test_first_author_is_contact_when_nobody_is_marked_and_nobody_has_email():
    paper = make_paper([Author(first_name="A", last_name="First"),
                        Author(first_name="B", last_name="Second")])
    assert contact_last_names(paper) == ["First"]


def test_priority_1_first_marked_corresponding_with_email():
    paper = make_paper([
        Author(first_name="A", last_name="First", email="a@example.com"),
        Author(first_name="B", last_name="Second", email="b@example.com", is_corresponding=True),
        Author(first_name="C", last_name="Third", email="c@example.com", is_corresponding=True),
    ])
    assert contact_last_names(paper) == ["Second"]


def test_priority_2_first_author_with_email():
    paper = make_paper([
        Author(first_name="A", last_name="First"),
        Author(first_name="B", last_name="Second", email="b@example.com"),
        Author(first_name="C", last_name="Third", email="c@example.com"),
    ])
    assert contact_last_names(paper) == ["Second"]


def test_priority_3_first_author_fallback():
    paper = make_paper([Author(first_name="A", last_name="First"),
                        Author(first_name="B", last_name="Second")])
    assert contact_last_names(paper) == ["First"]


def test_marked_corresponding_without_email_falls_back_to_first_with_email():
    paper = make_paper([
        Author(first_name="A", last_name="First", email="a@example.com"),
        Author(first_name="B", last_name="Second", is_corresponding=True),
    ])
    assert contact_last_names(paper) == ["First"]


# --- ProceedingsExport --------------------------------------------------------

def test_issue_tracking():
    export = ProceedingsExport(proceeding_id="2026-TEST", conference_name="TEST 2026")
    export.add_issue("warning", "test_category", "This is a test warning", paper_id=123)
    export.add_issue("error", "test_category", "This is a test error", paper_id=124, author_name="Test Author")
    assert len(export.validation_issues) == 2
    assert (export.error_count, export.warning_count) == (1, 1)
    assert export.has_errors and export.has_warnings


def test_statistics_count_unique_authors():
    john = dict(first_name="John", last_name="Doe", email="john@example.com")
    paper1 = make_paper([Author(**john), Author(first_name="Jane", last_name="Smith", email="jane@example.com")],
                        submission_id=1)
    paper2 = make_paper([Author(**john)], submission_id=2)  # same person as on paper 1
    export = ProceedingsExport()
    export.tracks.append(Track(original_name="Track A Original", section_name="Section A", papers=[paper1, paper2]))
    export.update_statistics()
    assert (export.total_papers, export.total_authors, export.unique_authors) == (2, 3, 2)


# --- Different affiliations / emails across papers ----------------------------

def export_with(*papers):
    export = ProceedingsExport()
    export.tracks.append(Track(original_name="Track", section_name="Section", papers=list(papers)))
    return export


def test_different_affiliations_across_papers_are_not_flagged():
    john = dict(first_name="John", last_name="Doe", email="john@example.com", country="USA")
    paper1 = make_paper([Author(**john, affiliation="MIT")], submission_id=1)
    paper2 = make_paper([Author(**john, affiliation="Stanford")], submission_id=2)
    assert [a.affiliation for p in (paper1, paper2) for a in p.authors] == ["MIT", "Stanford"]

    issues = validate_author_name_consistency(export_with(paper1, paper2))
    assert [i for i in issues if i.severity in ("error", "warning")] == []


def test_different_emails_across_papers_are_info_only():
    paper1 = make_paper([Author(first_name="Jane", last_name="Smith", email="jane@mit.edu", affiliation="MIT")],
                        submission_id=3)
    paper2 = make_paper([Author(first_name="Jane", last_name="Smith", email="jane@stanford.edu",
                                affiliation="Stanford")], submission_id=4)
    issues = validate_author_name_consistency(export_with(paper1, paper2))
    assert [i for i in issues if i.severity == "error"] == []
    assert [i.severity for i in issues] == ["info"]
