"""Generate a formatted Word document of committee members for the front matter.

Reads sheets from an Excel workbook, typically ``referees.xlsx`` written by
``scan_referees.py`` (one sheet per track and role). Choose sheets and their
headings with ``--section "SHEET=Heading:"`` (repeatable, in output order);
without it every sheet is used, headed by its sheet name.

Each sheet has columns: ``first name``, ``middle name`` (optional),
``last name``, ``affiliation`` (case-insensitive). The script writes a
``.docx`` file where:
    - Section headings (e.g. "Senior Program Committee:")
      are bold ``Linux Biolinum`` 10pt.
    - Names use ``Linux Libertine`` 11pt (regular).
    - Affiliations use ``Linux Libertine`` 11pt italic, wrapped in parentheses.

After writing, ``verify_against_excel`` re-parses the docx and asserts the
extracted (name, affiliation) tuples match the Excel rows exactly, in order.
"""

import argparse
import re
import sys

import pandas as pd
from docx import Document
from docx.shared import Pt
from docx.oxml.ns import qn

# Typography settings — must match the publisher's style guide.
HEADING_FONT = "Linux Biolinum"
HEADING_SIZE = Pt(10)
NAME_FONT = "Linux Libertine"
NAME_SIZE = Pt(11)


def style_run(run, font_name, size, *, bold=False, italic=False):
    """Apply font, size, and emphasis to a docx run.

    python-docx's high-level ``run.font.name = ...`` only sets the ASCII font
    slot. Word also consults the ``hAnsi``/``cs``/``eastAsia`` slots when
    rendering, so we set all four explicitly via the underlying ``w:rFonts``
    element. Without this, non-ASCII characters (accented names, CJK) can
    silently fall back to the default theme font.
    """
    run.font.name = font_name
    run.font.size = size
    run.bold = bold
    run.italic = italic

    # Ensure a <w:rFonts> child exists on the run's run-properties element,
    # then write the font name into every script slot Word might use.
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        from docx.oxml import OxmlElement
        rfonts = OxmlElement("w:rFonts")
        rpr.append(rfonts)
    for attr in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        rfonts.set(qn(attr), font_name)


def format_name(row: pd.Series) -> str:
    """Join ``first [middle] last`` from an Excel row into a single string.

    Middle name is included only when present and non-empty (NaN-safe).
    """
    parts = [str(row["first name"]).strip()]
    middle = row.get("middle name")
    if pd.notna(middle) and str(middle).strip():
        parts.append(str(middle).strip())
    parts.append(str(row["last name"]).strip())
    return " ".join(parts)


def add_entry_runs(paragraph, row: pd.Series) -> None:
    """Append three styled runs for one referee: ``Name (``, affiliation, ``)``.

    Split into separate runs so the affiliation alone can be italicized while
    the name and parentheses stay upright.
    """
    name_run = paragraph.add_run(format_name(row) + " (")
    style_run(name_run, NAME_FONT, NAME_SIZE)

    affil_run = paragraph.add_run(str(row["affiliation"]).strip())
    style_run(affil_run, NAME_FONT, NAME_SIZE, italic=True)

    close_run = paragraph.add_run(")")
    style_run(close_run, NAME_FONT, NAME_SIZE)


def add_section(doc: Document, heading: str, df: pd.DataFrame) -> None:
    """Append a labelled section of referees to the document.

    The first referee shares a paragraph with the bold heading (separated by
    four spaces, matching the requested layout); subsequent referees each get
    their own paragraph.
    """
    rows = list(df.iterrows())
    if not rows:
        return

    # First paragraph: heading + four spaces + first entry on the same line.
    first_para = doc.add_paragraph()
    heading_run = first_para.add_run(heading + "    ")
    style_run(heading_run, HEADING_FONT, HEADING_SIZE, bold=True)
    add_entry_runs(first_para, rows[0][1])

    # Remaining entries: one per paragraph.
    for _, row in rows[1:]:
        para = doc.add_paragraph()
        add_entry_runs(para, row)


def extract_entries(doc: Document, headings: list[str]) -> list[tuple[str, str]]:
    """Re-parse the docx into ``(name, affiliation)`` tuples in document order.

    Used by the verification step to round-trip the generated file. Section
    headings are stripped from the start of any paragraph that contains them
    so the leading entry on a heading line is still captured. Empty
    paragraphs (the blank separator between sections) are skipped.
    """
    entries = []
    # Greedy ``.*?`` for the name then a parenthesised affiliation at end-of-line.
    pattern = re.compile(r"^(.*?)\s*\(([^)]*)\)\s*$")

    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue

        # Strip the heading prefix if present so the inline first entry parses.
        for heading in sorted(headings, key=len, reverse=True):
            if text.startswith(heading):
                text = text[len(heading):].strip()
                break

        match = pattern.match(text)
        if match:
            entries.append((match.group(1).strip(), match.group(2).strip()))
    return entries


def verify_against_excel(doc_path: str, sections: list[tuple[str, pd.DataFrame]]) -> None:
    """Assert the docx contents match the Excel rows exactly and in order.

    Builds the expected list by concatenating the sections in the order the
    document is written in, parses the docx with ``extract_entries``, and
    compares element-by-element. Raises ``SystemExit`` on any count or
    content mismatch; prints up to 10 offending rows to stderr first.
    """
    expected = [
        (format_name(row), str(row["affiliation"]).strip())
        for _, df in sections
        for _, row in df.iterrows()
    ]
    actual = extract_entries(Document(doc_path), [heading for heading, _ in sections])

    if len(expected) != len(actual):
        raise SystemExit(
            f"Verification FAILED: expected {len(expected)} entries, found {len(actual)}"
        )

    mismatches = [
        (i, exp, act) for i, (exp, act) in enumerate(zip(expected, actual)) if exp != act
    ]
    if mismatches:
        for i, exp, act in mismatches[:10]:
            print(f"  row {i}: expected {exp!r}, got {act!r}", file=sys.stderr)
        raise SystemExit(f"Verification FAILED: {len(mismatches)} mismatched entries")

    print(f"Verification OK: {len(actual)} entries match Excel order exactly")


def load_sections(workbook: str, section_specs: list[str] | None = None) -> list[tuple[str, pd.DataFrame]]:
    """Return ``[(heading, rows)]`` from ``SHEET=Heading`` specs (default: every sheet)."""
    if not section_specs:
        section_specs = [f"{sheet}={sheet}:" for sheet in pd.ExcelFile(workbook).sheet_names]
    sections = []
    for spec in section_specs:
        sheet, _, heading = spec.partition("=")
        df = pd.read_excel(workbook, sheet_name=sheet.strip())
        df.columns = [str(c).strip().lower() for c in df.columns]
        sections.append((heading.strip() or f"{sheet.strip()}:", df))
    return sections


def write_committee_docx(sections: list[tuple[str, pd.DataFrame]], output: str) -> None:
    """Write the sections (blank paragraph between them), then verify the round trip."""
    doc = Document()
    for index, (heading, df) in enumerate(sections):
        if index:
            doc.add_paragraph()  # Blank paragraph separating sections.
        add_section(doc, heading, df)
    doc.save(output)
    counts = " + ".join(f"{len(df)} {heading.rstrip(':')}" for heading, df in sections)
    print(f"Wrote {output} ({counts})")

    # Round-trip the file we just wrote and confirm it matches the source.
    verify_against_excel(output, sections)


def main(argv: list[str] | None = None) -> None:
    """CLI entry point: load Excel, write docx, verify round-trip."""
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", default="referees.xlsx",
                        help="Excel workbook with one sheet per committee (default: referees.xlsx).")
    parser.add_argument("--section", action="append", metavar="SHEET=HEADING",
                        help='Sheet and heading, e.g. "Full Papers - SPC=Senior Program Committee:". '
                             "Repeat in output order. Default: every sheet.")
    parser.add_argument("--output", default="committee.docx",
                        help="Destination .docx path.")
    args = parser.parse_args(argv)

    write_committee_docx(load_sections(args.input, args.section), args.output)


if __name__ == "__main__":
    main()
