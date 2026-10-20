"""Regression tests for Author email validation."""

import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).parent.parent))

from proceedings.models import Author, Paper  # noqa: E402


@pytest.mark.parametrize("email", [
    "sean.o'brien@example.ie",
    "jörg@uni-münchen.de",
    "first+tag@sub.example.co.uk",
    "a@b.museum",
])
def test_valid_emails_are_kept(email):
    assert Author(first_name="A", last_name="B", email=email).email == email.lower()


@pytest.mark.parametrize("email", ["not-an-email", "two@@example.org", "a b@example.org", "a@example", "a@example."])
def test_malformed_emails_are_rejected(email):
    with pytest.raises(ValidationError):
        Author(first_name="A", last_name="B", email=email)


def test_apostrophe_email_keeps_its_owner_as_contact_author():
    authors = [
        Author(first_name="Sean", last_name="O'Brien", email="sean.o'brien@example.ie", is_corresponding=True),
        Author(first_name="Ann", last_name="Lee", email="ann@example.org", is_corresponding=True),
    ]
    paper = Paper(submission_id=1, title="T", authors=authors, track_name="t", section_name="", paper_type="Full Paper")
    assert [a.full_name for a in paper.corresponding_authors] == ["Sean O'Brien"]
