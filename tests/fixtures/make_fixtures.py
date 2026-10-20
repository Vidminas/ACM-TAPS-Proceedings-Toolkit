"""
Synthetic EasyChair exports for tests and for trying the notebook.

All people, emails and papers are invented. Each paper exercises one case:

  #1  Full paper (form field); authors listed out of order in the author rows;
      2nd AND last author marked corresponding  → contact must be the 2nd
  #2  Short paper (form field); address-style affiliation → affiliation_too_detailed
  #3  Demo (form field); nobody marked corresponding  → first author with email
  #4  'CHIIR 2027 DC' track, no form field  → Doctoral Consortium
  #5  Rejected  → not exported
  #6  Accepted in an unknown track  → 'uncategorised' error
  #7  Perspective paper  → Full Paper; non-ASCII name; author with blank
      affiliation filled from their other paper (#1)
  #8  Tutorial track; same author as #1 with a different affiliation (kept)

Usage:
    python tests/fixtures/make_fixtures.py [output_dir]   # default: tests/fixtures/data
"""

import sys
from pathlib import Path

import pandas as pd

TICK = "✔"

SUBMISSIONS = [
    # id, track, title, authors (true order), form fields, decision
    (1, "CHIIR 2027 PC", "Searching Together: Collaborative Query Formulation",
     "Ada Lovelace, Bram Visser and Chen Wei", "(Category) Full Paper", "accept"),
    (2, "CHIIR 2027 PC", "Short Notes on Relevance",
     "Dana Scully", "(Category) Short Paper", "probably accept"),
    (3, "CHIIR 2027 PC", "A Demo of Conversational Browsing",
     "Eli Novak and Fay Okafor", "(Category) Demonstration Paper", "accept"),
    (4, "CHIIR 2027 DC", "Doctoral Work on Search as Learning",
     "Gus Moreau", "", "accept"),
    (5, "CHIIR 2027 PC", "A Rejected Paper",
     "Hana Ito", "(Category) Full Paper", "reject"),
    (6, "CHIIR 2027 Misc", "An Uncategorised Paper",
     "Ivan Petrov", "", "accept"),
    (7, "CHIIR 2027 PC", "Perspectives on Interactive IR",
     "Zoë Ångström and Ada Lovelace", "(Category) Perspective Paper", "accept"),
    (8, "CHIIR 2027 Tutorials", "Tutorial: Running User Studies",
     "Ada Lovelace", "", "accept"),
]

AUTHORS = [
    # submission, first, last, email, country, affiliation, person id, corresponding
    (1, "Chen", "Wei", "chen.wei@example.edu", "China", "Example University", 103, True),
    (1, "Ada", "Lovelace", "ada@example.ac.uk", "United Kingdom", "University of Example", 101, False),
    (1, "Bram", "Visser", "bram@example.nl", "Netherlands", "Example Institute of Technology", 102, True),
    (2, "Dana", "Scully",
     "dana@example.ac.uk", "United Kingdom",
     "School of Computing, University of Example, 18 Example Street, Glasgow G12 8QQ, United Kingdom",
     104, True),
    (3, "Eli", "Novak", "eli@example.cz", "Czech Republic", "Example Technical University", 105, False),
    (3, "Fay", "Okafor", "fay@example.ng", "Nigeria", "University of Example Lagos", 106, False),
    (4, "Gus", "Moreau", "gus@example.fr", "France", "Université d'Exemple", 107, True),
    (5, "Hana", "Ito", "hana@example.jp", "Japan", "Example University Tokyo", 108, True),
    (6, "Ivan", "Petrov", "ivan@example.bg", "Bulgaria", "Example Academy", 109, True),
    (7, "Zoë", "Ångström", "zoe@example.se", "Sweden", "Exempel Universitet", 110, True),
    (7, "Ada", "Lovelace", "ada@example.ac.uk", "", "", 101, False),
    (8, "Ada", "Lovelace", "ada@example.ac.uk", "United Kingdom", "Example Analytical Engines Ltd", 101, True),
]


def submissions_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "#": sid, "Track #": 1, "Track name": track, "Title": title, "Authors": authors,
                "Submitted": "2026-10-01 12:00", "Last updated": "2026-10-08 09:30",
                "Form fields": form, "Keywords": "search\nusers", "Decision": decision,
                "Abstract": f"Abstract of {title}.",
            }
            for sid, track, title, authors, form, decision in SUBMISSIONS
        ]
    )


def authors_frame(csv_variant: bool = False) -> pd.DataFrame:
    """Excel column names, or the CSV download's names when csv_variant."""
    affiliation, corresponding = ("Organization", "Corresponding author") if csv_variant else ("Affiliation", "Corresponding?")
    mark = "yes" if csv_variant else TICK
    return pd.DataFrame(
        [
            {
                "Submission #": sid, "First name": first, "Last name": last, "Email": email,
                "Country": country, affiliation: aff, "Web page": "", "Person #": pid,
                corresponding: mark if corr else "",
            }
            for sid, first, last, email, country, aff, pid, corr in AUTHORS
        ]
    )


def taps_frame() -> pd.DataFrame:
    """A small ACM TAPS 'Export Metadata' sheet for the table-of-contents step."""
    return pd.DataFrame(
        [
            {"ORDER ID": 2, "PAPER TYPE": "Full Paper", "TITLE": "Perspectives on Interactive IR",
             "FIRST AUTHOR": "Zo&#x00EB; &#x00C5;ngstr&#x00F6;m",
             "OTHER AUTHORS": "Ada Lovelace!~!University of Example", "PDFPAGES": 11},
            {"ORDER ID": 1, "PAPER TYPE": "Full Paper",
             "TITLE": "Searching Together&#x003A; Collaborative Query Formulation",
             "FIRST AUTHOR": "Ada Lovelace",
             "OTHER AUTHORS": "Bram Visser!~!Example Institute of Technology!;!Chen Wei!~!Example University",
             "PDFPAGES": 12},
            {"ORDER ID": 3, "PAPER TYPE": "Short Paper", "TITLE": "Short Notes on Relevance",
             "FIRST AUTHOR": "Dana Scully", "OTHER AUTHORS": "", "PDFPAGES": 5},
        ]
    )


def write_fixtures(out_dir) -> dict:
    """Write export.xlsx, submission.csv, author.csv and ExportMetadata.xlsx; return their paths."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths = {
        "xlsx": out / "export.xlsx",
        "submission_csv": out / "submission.csv",
        "author_csv": out / "author.csv",
        "taps_xlsx": out / "ExportMetadata.xlsx",
    }
    with pd.ExcelWriter(paths["xlsx"]) as writer:
        submissions_frame().to_excel(writer, sheet_name="Submissions", index=False)
        authors_frame().to_excel(writer, sheet_name="Authors", index=False)
    submissions_frame().to_csv(paths["submission_csv"], index=False)
    authors_frame(csv_variant=True).to_csv(paths["author_csv"], index=False)
    taps_frame().to_excel(paths["taps_xlsx"], index=False)
    return paths


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else Path(__file__).parent / "data"
    for name, path in write_fixtures(target).items():
        print(f"{name}: {path}")
