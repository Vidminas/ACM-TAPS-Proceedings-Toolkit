#!/usr/bin/env python3
"""
Author: Niall McGuire (PhD)
Email: niall.mcguire@strath.ac.uk


CHIIR Table of Contents Generator
Reads metadata from the ACM TAPS export Excel file and generates a formatted
table of contents with cumulative page numbers.

Usage:
    python generate_toc.py <ExportMetadata.xlsx> [output_name]

    output_name defaults to 'chiir_toc' (produces chiir_toc.txt and chiir_toc.csv)

Expected Excel columns:
    ORDER ID      - Integer ordering for proceedings sequence
    PAPER TYPE    - Category label (e.g. 'Full Paper', 'Short Paper')
    TITLE         - Paper title (may contain HTML entities)
    OTHER AUTHORS - Semicolon-delimited author+affiliation string
    FIRST AUTHOR  - First/corresponding author name (separate column)
    PDFPAGES      - Integer page count for this paper
"""

import sys
import os
import html
import pandas as pd


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

def clean_html_entities(text: str) -> str:
    """Convert HTML entities (e.g. &#x002C;) to their proper characters."""
    if not isinstance(text, str):
        return str(text) if text is not None else ""
    return html.unescape(text)


def parse_other_authors(other_authors_str) -> list[str]:
    """
    Extract author names from the OTHER AUTHORS field.
    Expected format: "Name!~!Affiliation!;!Name2!~!Affiliation2..."
    """
    if pd.isna(other_authors_str) or other_authors_str == "":
        return []

    authors = []
    for entry in str(other_authors_str).split("!;!"):
        if "!~!" in entry:
            name = entry.split("!~!")[0].strip()
            if name:
                authors.append(name)
    return authors


def build_author_list(row: pd.Series) -> list[str]:
    """
    Combine FIRST AUTHOR (if present as its own column) with OTHER AUTHORS.
    Falls back gracefully if the column does not exist.
    """
    authors = []

    # Prepend the first/corresponding author if it lives in its own column
    if "FIRST AUTHOR" in row.index and pd.notna(row["FIRST AUTHOR"]):
        first = clean_html_entities(str(row["FIRST AUTHOR"])).strip()
        if first:
            authors.append(first)

    authors.extend(parse_other_authors(row.get("OTHER AUTHORS", "")))
    return authors


def format_authors(authors: list[str]) -> str:
    """Format as 'A, B and C'."""
    if not authors:
        return ""
    if len(authors) == 1:
        return authors[0]
    if len(authors) == 2:
        return f"{authors[0]} and {authors[1]}"
    return ", ".join(authors[:-1]) + " and " + authors[-1]


# ---------------------------------------------------------------------------
# TOC formatting
# ---------------------------------------------------------------------------

LINE_WIDTH = 80


def format_toc_line(title: str, page: int) -> str:
    """
    Return a single dot-leader line:
        Paper Title ········ 42
    The dots fill the gap between the title and right-aligned page number.
    """
    page_str = str(page)
    # +2 accounts for the spaces either side of the dot run
    available = LINE_WIDTH - len(title) - len(page_str) - 2
    dots = "·" * max(3, available)
    return f"{title} {dots} {page_str}"


# ---------------------------------------------------------------------------
# Main generator
# ---------------------------------------------------------------------------

def generate_toc(excel_path: str, output_stem: str = "chiir_toc"):
    """
    Generate table of contents from a TAPS metadata Excel file.

    Args:
        excel_path:   Path to ExportMetadata.xlsx
        output_stem:  Base name (no extension) for output files.
                      Produces <output_stem>.txt and <output_stem>.csv
    """
    output_txt = output_stem + ".txt"
    output_csv = output_stem + ".csv"

    print(f"Reading metadata from: {excel_path}")
    df = pd.read_excel(excel_path)

    required_cols = {"ORDER ID", "PAPER TYPE", "TITLE", "PDFPAGES"}
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"Excel file is missing required columns: {missing}")

    df = df.sort_values("ORDER ID").reset_index(drop=True)

    # --- Build flat records with start pages ----------------------------
    records = []
    current_page = 1

    for _, row in df.iterrows():
        title = clean_html_entities(row["TITLE"])
        authors = build_author_list(row)
        authors_str = format_authors(authors)
        page_count = int(row["PDFPAGES"])
        paper_type = str(row["PAPER TYPE"])

        records.append({
            "paper_type": paper_type,
            "title": title,
            "authors": authors_str,
            "start_page": current_page,
            "end_page": current_page + page_count - 1,
            "page_count": page_count,
        })
        current_page += page_count

    # --- Text TOC -------------------------------------------------------
    toc_lines = [
        "=" * LINE_WIDTH,
        "TABLE OF CONTENTS",
        "=" * LINE_WIDTH,
        "",
    ]

    # Group by paper type in the order they first appear
    seen_types: list[str] = []
    for r in records:
        if r["paper_type"] not in seen_types:
            seen_types.append(r["paper_type"])

    for paper_type in seen_types:
        toc_lines.append(paper_type.upper())
        toc_lines.append("-" * LINE_WIDTH)

        for r in records:
            if r["paper_type"] != paper_type:
                continue
            toc_lines.append(format_toc_line(r["title"], r["start_page"]))
            toc_lines.append(f"  {r['authors']}")
            toc_lines.append("")

        toc_lines.append("")

    toc_text = "\n".join(toc_lines)

    # --- Write text file ------------------------------------------------
    with open(output_txt, "w", encoding="utf-8") as f:
        f.write(toc_text)
    print(f"Text TOC  → {output_txt}")

    # --- Write CSV ------------------------------------------------------
    csv_df = pd.DataFrame(records).rename(columns={
        "paper_type": "Paper Type",
        "title": "Title",
        "authors": "Authors",
        "start_page": "Start Page",
        "end_page": "End Page",
        "page_count": "Page Count",
    })
    csv_df.to_csv(output_csv, index=False, encoding="utf-8")
    print(f"CSV TOC   → {output_csv}")

    # --- Summary --------------------------------------------------------
    print(f"\nTotal papers : {len(csv_df)}")
    print(f"Total pages  : {csv_df['End Page'].iloc[-1]}")
    print("\nBreakdown by paper type:")
    summary = (
        csv_df.groupby("Paper Type")
        .agg(Papers=("Title", "count"), Pages=("Page Count", "sum"))
    )
    print(summary.to_string())

    return toc_text, csv_df


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    excel_path = sys.argv[1]
    output_stem = sys.argv[2] if len(sys.argv) > 2 else "chiir_toc"

    # Strip a trailing extension if the user passed a full filename
    if "." in os.path.basename(output_stem):
        output_stem = os.path.splitext(output_stem)[0]

    generate_toc(excel_path, output_stem)