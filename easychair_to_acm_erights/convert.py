#!/usr/bin/env python3
"""
Author: Niall McGuire (PhD)
Email: niall.mcguire@strath.ac.uk

CHIIR EasyChair → ACM eRights CSV Converter
Outputs one CSV per paper type plus a combined CSV file.
36-column Enhanced CSV format (ACM 2024+).

Includes papers with decision 'accept' OR 'probably accept'.

Usage:
    python convert.py <submission.csv> <author.csv> <event_id>

    event_id  - ACM event ID provided in your eRights confirmation email
                (e.g. 3726522).  Required; the script will not run without it.

Input files are exported directly from EasyChair:
    submission.csv  →  Submissions → Download → All Submissions (CSV)
    author.csv      →  Submissions → Download → Authors (CSV)

Output files (written to the current directory):
    CHIIR-<YEAR>-Full-Papers.csv
    CHIIR-<YEAR>-Short-Papers.csv
    CHIIR-<YEAR>-Demonstrations.csv
    CHIIR-<YEAR>-Doctoral-Consortium.csv
    CHIIR-<YEAR>-Tutorials.csv
    CHIIR-<YEAR>-Workshops.csv
    CHIIR-<YEAR>-All-Papers.csv   ← combined
"""

import csv
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration — update these each year
# ---------------------------------------------------------------------------

YEAR = "2026"

PAPER_TYPE_DISPLAY = {
    "research-article": "Full Paper",
    "short-paper":      "Short Paper",
    "demonstration":    "Demonstration Paper",
    "work-in-progress": "Doctoral Consortium",
    "tutorial":         "Tutorial",
    "extended-abstract":"Workshop",
}

CATEGORY_ORDER = [
    "research-article",
    "short-paper",
    "demonstration",
    "work-in-progress",
    "tutorial",
    "extended-abstract",
]

FILENAME_MAP = {
    "research-article": f"CHIIR-{YEAR}-Full-Papers.csv",
    "short-paper":      f"CHIIR-{YEAR}-Short-Papers.csv",
    "demonstration":    f"CHIIR-{YEAR}-Demonstrations.csv",
    "work-in-progress": f"CHIIR-{YEAR}-Doctoral-Consortium.csv",
    "tutorial":         f"CHIIR-{YEAR}-Tutorials.csv",
    "extended-abstract":f"CHIIR-{YEAR}-Workshops.csv",
}

ACCEPTED_DECISIONS = {"accept", "probably accept"}

# ---------------------------------------------------------------------------
# Text cleaning
# ---------------------------------------------------------------------------

def clean_text(text: str) -> str:
    """Remove or replace characters that cause issues in CSV/ACM ingest."""
    if not text:
        return text
    text = text.replace("\uf8ff", "")   # Apple logo
    text = text.replace("\u2028", " ")  # Line separator
    text = text.replace("\u2029", " ")  # Paragraph separator
    return text

# ---------------------------------------------------------------------------
# EasyChair parsing — uses header row, not positional indices
# ---------------------------------------------------------------------------

def parse_submission_csv(submission_csv: str):
    """
    Extract accepted papers from EasyChair submission export.

    Returns:
        papers_by_category  dict[str, list[str]]   category → [paper_id]
        titles              dict[str, str]
        abstracts           dict[str, str]
        submission_dates    dict[str, str]
        approval_dates      dict[str, str]
        decision_counts     dict[str, int]
    """
    papers_by_category = {k: [] for k in PAPER_TYPE_DISPLAY}
    titles, abstracts, submission_dates, approval_dates = {}, {}, {}, {}
    decision_counts: dict[str, int] = {}

    try:
        f = open(submission_csv, "r", encoding="utf-8")
        # Try UTF-8 first; fall back to mac_roman if it fails
    except UnicodeDecodeError:
        f = open(submission_csv, "r", encoding="mac_roman")

    with f:
        reader = csv.DictReader(f, quoting=csv.QUOTE_ALL)

        # Normalise header names to lowercase for resilience against
        # minor formatting changes between EasyChair versions
        reader.fieldnames = [h.strip().lower() for h in reader.fieldnames]

        for row in reader:
            paper_id   = row.get("#", row.get("id", "")).strip()
            track_name = row.get("track name", row.get("track", "")).strip()
            title      = row.get("title", "").strip()
            submitted  = row.get("submitted", row.get("submission date", "")).strip()
            updated    = row.get("last updated", row.get("updated", "")).strip()
            form_fields= row.get("form fields", row.get("keywords", "")).strip()
            decision   = row.get("decision", "").strip().lower()
            abstract   = row.get("abstract", "").strip()

            if not paper_id:
                continue

            decision_counts[decision] = decision_counts.get(decision, 0) + 1

            if decision not in ACCEPTED_DECISIONS:
                continue

            titles[paper_id]           = title
            abstracts[paper_id]        = abstract
            submission_dates[paper_id] = submitted
            approval_dates[paper_id]   = updated

            # --- Categorise ------------------------------------------------
            ff = form_fields.lower()
            tn = track_name.lower()

            if "(category) full paper" in ff or "(category) resource paper" in ff \
                    or "(category) perspective paper" in ff or "(category) perspective" in ff:
                papers_by_category["research-article"].append(paper_id)

            elif "(category) demonstration paper" in ff or "(category) demonstration" in ff:
                papers_by_category["demonstration"].append(paper_id)

            elif "(category) short paper" in ff:
                papers_by_category["short-paper"].append(paper_id)

            elif "chiir" in tn and "dc" in tn:
                papers_by_category["work-in-progress"].append(paper_id)

            elif "chiir" in tn and "short" in tn:
                papers_by_category["short-paper"].append(paper_id)

            elif "tutorial" in tn:
                papers_by_category["tutorial"].append(paper_id)

            elif "workshop" in tn:
                papers_by_category["extended-abstract"].append(paper_id)

            elif "chiir" in tn and "pc" in tn:
                papers_by_category["research-article"].append(paper_id)

            else:
                print(f"  WARNING: Paper {paper_id} accepted but not categorised!")
                print(f"    Track      : {track_name}")
                print(f"    Form fields: {form_fields}")

    return (papers_by_category, titles, abstracts,
            submission_dates, approval_dates, decision_counts)


def parse_author_csv(author_csv: str, paper_ids: set) -> dict:
    """
    Extract author details for a given set of paper IDs.

    Returns:
        authors  dict[paper_id, list[(first, last, seq, contact, email,
                                      institution, country)]]
    """
    authors: dict[str, list] = {}
    seq_counter: dict[str, int] = {}

    with open(author_csv, "r", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f, quoting=csv.QUOTE_ALL)
        reader.fieldnames = [h.strip().lower() for h in reader.fieldnames]

        for row in reader:
            paper_id = row.get("submission #", row.get("#", row.get("id", ""))).strip()
            if paper_id not in paper_ids:
                continue

            first       = row.get("first name", "").strip()
            last        = row.get("last name", "").strip()
            email       = row.get("email", "").strip()
            country     = row.get("country", "").strip()
            affiliation = row.get("organization", row.get("affiliation", row.get("institution", ""))).strip()
            corresponding = row.get("corresponding author", row.get("corresponding", "")).strip()

            if paper_id not in authors:
                authors[paper_id] = []
                seq_counter[paper_id] = 1

            authors[paper_id].append((
                first, last, seq_counter[paper_id],
                corresponding, email, affiliation, country
            ))
            seq_counter[paper_id] += 1

    return authors

# ---------------------------------------------------------------------------
# CSV writing
# ---------------------------------------------------------------------------

# Constant empty fields present in every row
_EMPTY = [""] * 5   # prefix, middle_name, suffix, ACM_profile_id, ACM_client_no

def _build_row(event_id, paper_id, paper_type_display, title,
               first, last, seq, contact, email, institution, country,
               submitted, approved, abstract):
    """Assemble a single 36-column ACM eRights row."""
    return [
        event_id,            # 1  Event ID
        paper_id,            # 2  Paper ID
        paper_type_display,  # 3  Paper type
        title,               # 4  Title
        "",                  # 5  Prefix
        clean_text(first),   # 6  First name
        "",                  # 7  Middle name
        clean_text(last),    # 8  Last name
        "",                  # 9  Suffix
        seq,                 # 10 Author sequence
        contact,             # 11 Corresponding author
        "",                  # 12 ACM profile ID
        "",                  # 13 ACM client number
        "",                  # 14 ORCID
        email,               # 15 Email
        "",                  # 16 Department/school/lab
        clean_text(institution), # 17 Institution
        "",                  # 18 City
        "",                  # 19 State/province
        country,             # 20 Country
        "",                  # 21–25 Secondary affiliation fields
        "", "", "", "",
        "",                  # 26 Section title
        "",                  # 27 Section seq no
        "",                  # 28 Published article number
        "",                  # 29 Start page
        "",                  # 30 End page
        "",                  # 31 Article seq no
        submitted,           # 32 Submission date
        approved,            # 33 Approval date
        "EasyChair",         # 34 Source
        clean_text(abstract),# 35 Abstract
        "",                  # 36 Role
    ]


def write_category_csv(paper_ids: list, titles, abstracts, submission_dates,
                       approval_dates, authors, output_file: str,
                       paper_type: str, event_id: str):
    """Write a single-category ACM CSV file."""
    paper_type_display = PAPER_TYPE_DISPLAY.get(paper_type, paper_type)
    row_count = 0

    with open(output_file, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter=",", quotechar='"', quoting=csv.QUOTE_MINIMAL)

        for pid in sorted(paper_ids, key=int):
            title    = clean_text(titles[pid])
            abstract = clean_text(abstracts.get(pid, ""))
            sub_date = submission_dates.get(pid, "")
            app_date = approval_dates.get(pid, "")

            for first, last, seq, contact, email, inst, country in authors.get(pid, []):
                writer.writerow(_build_row(
                    event_id, pid, paper_type_display, title,
                    first, last, seq, contact, email, inst, country,
                    sub_date, app_date, abstract
                ))
                row_count += 1

    return row_count


def write_combined_csv(papers_by_category, titles, abstracts, submission_dates,
                       approval_dates, authors, output_file: str, event_id: str):
    """Write all categories to a single combined ACM CSV file."""
    row_count = 0

    with open(output_file, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter=",", quotechar='"', quoting=csv.QUOTE_MINIMAL)

        for category in CATEGORY_ORDER:
            paper_ids = papers_by_category.get(category, [])
            if not paper_ids:
                continue

            paper_type_display = PAPER_TYPE_DISPLAY[category]

            for pid in sorted(paper_ids, key=int):
                title    = clean_text(titles[pid])
                abstract = clean_text(abstracts.get(pid, ""))
                sub_date = submission_dates.get(pid, "")
                app_date = approval_dates.get(pid, "")

                for first, last, seq, contact, email, inst, country in authors.get(pid, []):
                    writer.writerow(_build_row(
                        event_id, pid, paper_type_display, title,
                        first, last, seq, contact, email, inst, country,
                        sub_date, app_date, abstract
                    ))
                    row_count += 1

    return row_count

# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) != 4:
        print(__doc__)
        print("Error: exactly 3 arguments required.")
        sys.exit(1)

    submission_csv, author_csv, event_id = sys.argv[1], sys.argv[2], sys.argv[3]

    # Refuse to run with a placeholder event ID
    if not event_id.strip() or event_id.lower().startswith("placeholder"):
        print("Error: a valid ACM event ID must be provided as the third argument.")
        print("  You can find it in your ACM eRights confirmation email.")
        sys.exit(1)

    print("=" * 70)
    print(f"CHIIR {YEAR} — ACM eRights Conversion")
    print("=" * 70)
    print(f"Event ID    : {event_id}")
    print(f"Submissions : {submission_csv}")
    print(f"Authors     : {author_csv}")
    print()

    # --- Parse submissions -----------------------------------------------
    print("Parsing submission.csv …")
    (papers_by_category, titles, abstracts,
     submission_dates, approval_dates,
     decision_counts) = parse_submission_csv(submission_csv)

    print("\nDecision breakdown:")
    print("-" * 40)
    for decision, count in sorted(decision_counts.items()):
        marker = "  ✓ included" if decision in ACCEPTED_DECISIONS else ""
        print(f"  {decision:<22} {count:>3}{marker}")
    print("-" * 40)

    all_paper_ids = [pid for pids in papers_by_category.values() for pid in pids]
    print(f"\n{len(all_paper_ids)} accepted papers found.")

    # --- Parse authors ---------------------------------------------------
    print("\nParsing author.csv …")
    authors = parse_author_csv(author_csv, set(all_paper_ids))
    print(f"Author data loaded for {len(authors)} papers.")

    missing = set(all_paper_ids) - set(authors)
    if missing:
        print(f"\nWARNING: No author data for {len(missing)} paper(s): "
              f"{sorted(missing, key=int)}")

    # --- Per-category CSV files ------------------------------------------
    print("\nWriting per-category CSV files:")
    print("-" * 70)

    total_papers = 0
    for category in CATEGORY_ORDER:
        paper_ids = papers_by_category.get(category, [])
        if not paper_ids:
            continue

        filename = FILENAME_MAP[category]
        rows = write_category_csv(
            paper_ids, titles, abstracts,
            submission_dates, approval_dates,
            authors, filename, category, event_id
        )
        print(f"  {filename:<50} {len(paper_ids):>3} papers  ({rows} rows)")
        total_papers += len(paper_ids)

    print("-" * 70)
    print(f"  Total: {total_papers} papers")

    # --- Combined CSV file -----------------------------------------------
    print("\nWriting combined CSV file:")
    combined = f"CHIIR-{YEAR}-All-Papers.csv"
    rows = write_combined_csv(
        papers_by_category, titles, abstracts,
        submission_dates, approval_dates,
        authors, combined, event_id
    )
    print(f"  {combined}  ({rows} rows)")

    print("\n" + "=" * 70)
    print("Done.")
    print("=" * 70)


if __name__ == "__main__":
    main()