"""
EasyChair Export Formatters
===========================

This module provides exporters for different output formats (XML, eRights
CSV, TXT, MD, heading preview)
that work with validated Pydantic models.

Usage:
    from proceedings.exporters import export_to_xml, export_to_erights_csv, export_to_text

    export_to_xml(proceedings_export, "output.xml")
    export_to_erights_csv(proceedings_export, "out/", event_id="1234567", config=config)
    export_to_text(proceedings_export, "output.txt", format_type="txt")
"""

import csv
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional, Literal
import logging
from datetime import datetime

from .config import ConferenceConfig
from .models import ProceedingsExport, Track, Paper, Author


def indent_xml(elem, level=0):
    """
    Add pretty-printing indentation to XML elements.

    Args:
        elem: XML Element to indent
        level: Current indentation level (default: 0)
    """
    i = "\n" + level * "  "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "
        for child in elem:
            indent_xml(child, level + 1)
        if not child.tail or not child.tail.strip():
            child.tail = i
    if level and (not elem.tail or not elem.tail.strip()):
        elem.tail = i


def format_date(dt: Optional[datetime]) -> str:
    """
    Convert datetime to ACM format (DD-MON-YYYY).

    Args:
        dt: datetime object

    Returns:
        Formatted date string (e.g., "09-APR-2026") or empty string if None
    """
    if dt is None:
        return ""
    return dt.strftime("%d-%b-%Y").upper()


def clean_affiliation_string(affiliation_str: Optional[str]) -> str:
    """
    Clean affiliation string by stripping whitespace and leading/trailing punctuation.

    Handles common data quality issues like:
    - ", Tsinghua University" → "Tsinghua University"
    - "MIT, " → "MIT"
    - " , Stanford University" → "Stanford University"

    Args:
        affiliation_str: Raw affiliation string

    Returns:
        str: Cleaned affiliation string
    """
    if not affiliation_str:
        return ""

    # Strip whitespace
    cleaned = affiliation_str.strip()

    # Strip leading/trailing punctuation (commas, semicolons, periods, etc.)
    # Keep stripping until no more leading/trailing punctuation+whitespace
    while cleaned and cleaned[0] in '.,;:-_':
        cleaned = cleaned[1:].strip()
    while cleaned and cleaned[-1] in '.,;:-_':
        cleaned = cleaned[:-1].strip()

    return cleaned


def export_to_xml(
    export: ProceedingsExport,
    output_file: str,
    source: str = "EasyChair",
    logger: Optional[logging.Logger] = None
) -> None:
    """
    Export proceedings to ACM/Sheridan XML format.

    Args:
        export: Validated ProceedingsExport object
        output_file: Output XML file path
        source: Source system name
        logger: Optional logger instance
    """
    if logger is None:
        logger = logging.getLogger(__name__)

    logger.info("Generating ACM XML...")

    # Create XML root
    root = ET.Element("erights_record")
    parent = ET.SubElement(root, "parent_data")
    ET.SubElement(parent, "proceeding").text = export.proceeding_id or ""
    ET.SubElement(parent, "volume").text = ""
    ET.SubElement(parent, "issue").text = ""
    ET.SubElement(parent, "issue_date").text = ""
    ET.SubElement(parent, "source").text = source

    paper_seq = 1

    # Process each track and paper
    for track in export.tracks:
        for paper in track.papers:
            paper_xml = ET.SubElement(root, "paper")

            # Paper metadata
            ET.SubElement(paper_xml, "paper_type").text = paper.paper_type
            ET.SubElement(paper_xml, "art_submission_date").text = format_date(paper.submitted_date)
            ET.SubElement(paper_xml, "art_approval_date").text = format_date(paper.approval_date)
            ET.SubElement(paper_xml, "paper_title").text = paper.title

            # Event tracking number (prefix from the conference config)
            ET.SubElement(paper_xml, "event_tracking_number").text = (
                paper.event_tracking_number or f"paper{paper.submission_id}"
            )
            ET.SubElement(paper_xml, "published_article_number").text = ""
            ET.SubElement(paper_xml, "start_page").text = ""
            ET.SubElement(paper_xml, "end_page").text = ""

            # Authors
            authors_xml = ET.SubElement(paper_xml, "authors")

            for author_seq, author in enumerate(paper.authors, start=1):
                author_xml = ET.SubElement(authors_xml, "author")

                # Author name
                ET.SubElement(author_xml, "prefix").text = ""
                ET.SubElement(author_xml, "first_name").text = author.first_name
                ET.SubElement(author_xml, "middle_name").text = ""
                ET.SubElement(author_xml, "last_name").text = author.last_name
                ET.SubElement(author_xml, "suffix").text = ""

                # Affiliations
                affiliations_xml = ET.SubElement(author_xml, "affiliations")
                affiliation_xml = ET.SubElement(affiliations_xml, "affiliation")

                # No parsing - just map Affiliation to institution
                ET.SubElement(affiliation_xml, "department").text = ""
                ET.SubElement(affiliation_xml, "institution").text = clean_affiliation_string(author.affiliation)
                ET.SubElement(affiliation_xml, "city").text = ""
                ET.SubElement(affiliation_xml, "state_province").text = ""
                ET.SubElement(affiliation_xml, "country").text = author.country or ""
                ET.SubElement(affiliation_xml, "sequence_no").text = "1"

                # Author metadata
                ET.SubElement(author_xml, "email_address").text = author.email or ""
                ET.SubElement(author_xml, "sequence_no").text = str(author_seq)
                ET.SubElement(author_xml, "contact_author").text = "Y" if author.is_corresponding else "N"
                ET.SubElement(author_xml, "ACM_profile_id").text = ""
                ET.SubElement(author_xml, "ACM_client_no").text = ""
                ET.SubElement(author_xml, "ORCID").text = ""
                ET.SubElement(author_xml, "role").text = "author"

            # Paper section and sequence
            ET.SubElement(paper_xml, "section").text = paper.section_name
            ET.SubElement(paper_xml, "sequence_no").text = str(paper_seq)

            paper_seq += 1

    # Write XML
    indent_xml(root)
    tree = ET.ElementTree(root)
    tree.write(output_file, encoding="utf-8", xml_declaration=True)

    logger.info(f"✓ XML generated: {output_file}")


def export_to_text(
    export: ProceedingsExport,
    output_file: str,
    format_type: Literal["txt", "md"] = "txt",
    logger: Optional[logging.Logger] = None
) -> None:
    """
    Export proceedings to text or markdown format.

    Args:
        export: Validated ProceedingsExport object
        output_file: Output file path
        format_type: Output format ("txt" or "md")
        logger: Optional logger instance
    """
    if logger is None:
        logger = logging.getLogger(__name__)

    logger.info(f"Generating {format_type.upper()} output...")

    with open(output_file, "w", encoding="utf-8") as f:
        for track_idx, track in enumerate(export.tracks):
            # Track header
            if format_type == "md":
                f.write(f"# {track.section_name}\n")
            else:
                f.write(f"{track.section_name}\n")

            # Papers
            for paper in track.papers:
                if format_type == "md":
                    f.write(f"## {paper.title}\n")
                else:
                    f.write(f"{paper.title}\n")

                for author in paper.authors:
                    if author.affiliation:
                        f.write(f"{author.full_name}, {author.affiliation}\n")
                    else:
                        f.write(f"{author.full_name}\n")

                f.write("\n")

            # Extra blank line between tracks (but not after the last track)
            if track_idx < len(export.tracks) - 1:
                f.write("\n")

    logger.info(f"✓ {format_type.upper()} file generated: {output_file}")


def clean_csv_text(text: Optional[str]) -> str:
    """Remove characters that break CSV/ACM ingest (from the CHIIR 2026 converter)."""
    if not text:
        return ""
    text = text.replace("", "")   # Apple logo
    text = text.replace(" ", " ")  # Line separator
    text = text.replace(" ", " ")  # Paragraph separator
    return text


ERIGHTS_CSV_COLUMNS = 36


def erights_row(event_id: str, paper: Paper, author: Author, seq: int) -> List[str]:
    """Assemble a single 36-column ACM eRights row (Enhanced CSV format, 2024+)."""
    return [
        event_id,                                   # 1  Event ID
        paper.event_tracking_number or str(paper.submission_id),  # 2  Paper ID
        paper.paper_type,                           # 3  Paper type
        clean_csv_text(paper.title),                # 4  Title
        "",                                         # 5  Prefix
        clean_csv_text(author.first_name),          # 6  First name
        "",                                         # 7  Middle name
        clean_csv_text(author.last_name),           # 8  Last name
        "",                                         # 9  Suffix
        str(seq),                                   # 10 Author sequence
        "Y" if author.is_corresponding else "N",    # 11 Corresponding author
        "",                                         # 12 ACM profile ID
        "",                                         # 13 ACM client number
        "",                                         # 14 ORCID
        author.email or "",                         # 15 Email
        "",                                         # 16 Department/school/lab
        clean_csv_text(clean_affiliation_string(author.affiliation)),  # 17 Institution
        "",                                         # 18 City
        "",                                         # 19 State/province
        author.country or "",                       # 20 Country
        "", "", "", "", "",                         # 21–25 Secondary affiliation fields
        paper.section_name,                         # 26 Section title
        "",                                         # 27 Section seq no
        "",                                         # 28 Published article number
        "",                                         # 29 Start page
        "",                                         # 30 End page
        "",                                         # 31 Article seq no
        format_date(paper.submitted_date),          # 32 Submission date
        format_date(paper.approval_date),           # 33 Approval date
        "EasyChair",                                # 34 Source
        clean_csv_text(paper.abstract),             # 35 Abstract
        "",                                         # 36 Role
    ]


def export_to_erights_csv(
    export: ProceedingsExport,
    output_dir: str,
    event_id: str,
    config: ConferenceConfig,
    logger: Optional[logging.Logger] = None
) -> Dict[str, Path]:
    """
    Export to ACM eRights CSV: one file per paper type plus a combined file.

    Files are named '<NAME>-<YEAR>-<file stem>.csv' and '<NAME>-<YEAR>-All-Papers.csv'.
    Like the CHIIR 2026 files, they have no header row.

    Returns:
        Mapping of paper type (and 'All') to the file written
    """
    if logger is None:
        logger = logging.getLogger(__name__)
    if not str(event_id).strip() or str(event_id).lower().startswith("placeholder"):
        raise ValueError("A valid ACM event ID is required (see your eRights confirmation email)")

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    prefix = f"{config.name}-{config.year}"
    written: Dict[str, Path] = {}
    all_rows: List[List[str]] = []

    logger.info("Generating eRights CSV files...")
    for track in export.tracks:
        paper_type = config.paper_type(track.section_name)
        stem = paper_type.csv_stem if paper_type else track.section_name.replace(" ", "-")
        rows = [
            erights_row(str(event_id), paper, author, seq)
            for paper in track.papers
            for seq, author in enumerate(paper.authors, start=1)
        ]
        path = out / f"{prefix}-{stem}.csv"
        _write_csv(path, rows)
        written[track.section_name] = path
        all_rows.extend(rows)
        logger.info(f"  {path.name:<50} {track.paper_count:>3} papers  ({len(rows)} rows)")

    combined = out / f"{prefix}-All-Papers.csv"
    _write_csv(combined, all_rows)
    written["All"] = combined
    logger.info(f"  {combined.name:<50} {export.total_papers:>3} papers  ({len(all_rows)} rows)")
    return written


def _write_csv(path: Path, rows: List[List[str]]) -> None:
    with open(path, "w", encoding="utf-8", newline="") as f:
        csv.writer(f, quoting=csv.QUOTE_MINIMAL).writerows(rows)


def heading_previews(export: ProceedingsExport) -> List[Dict[str, str]]:
    """
    One block per paper showing what will be uploaded to eRights, i.e. what
    TAPS will print in the paper heading, and who receives ACM's emails.

    Returns:
        List of dicts with paper_id, tracking_number, contact_name, contact_email, text
    """
    previews = []
    for track in export.tracks:
        for paper in track.papers:
            contact = paper.corresponding_authors[0] if paper.corresponding_authors else None
            lines = [
                f"Paper #{paper.submission_id} ({paper.event_tracking_number}) — {paper.paper_type}",
                paper.title,
                "",
            ]
            for seq, author in enumerate(paper.authors, start=1):
                institution = clean_affiliation_string(author.affiliation) or "(no affiliation)"
                country = author.country or "(no country)"
                marker = "   ← contact author (receives ACM emails)" if author is contact else ""
                lines.append(f"  {seq}. {author.full_name}{marker}")
                lines.append(f"     {institution}, {country}")
                lines.append(f"     {author.email or '(no email)'}")
            previews.append({
                "paper_id": str(paper.submission_id),
                "tracking_number": paper.event_tracking_number or "",
                "contact_name": contact.full_name if contact else "",
                "contact_email": (contact.email or "") if contact else "",
                "text": "\n".join(lines),
            })
    return previews


def export_preview(
    export: ProceedingsExport,
    output_file: str,
    logger: Optional[logging.Logger] = None
) -> None:
    """Write all heading previews to a text file."""
    if logger is None:
        logger = logging.getLogger(__name__)
    blocks = [p["text"] for p in heading_previews(export)]
    Path(output_file).write_text("\n\n".join(blocks) + "\n", encoding="utf-8")
    logger.info(f"✓ Heading preview generated: {output_file}")


def print_summary(
    export: ProceedingsExport,
    logger: logging.Logger
) -> None:
    """
    Print a summary of the export.

    Args:
        export: ProceedingsExport to summarize
        logger: Logger instance
    """
    logger.info("")
    logger.info("=" * 80)
    logger.info("EXPORT SUMMARY")
    logger.info("=" * 80)
    logger.info("")
    if export.decision_counts:
        logger.info("EasyChair decisions:")
        for decision, count in export.decision_counts.items():
            logger.info(f"  {decision:<30} {count:>4}")
        logger.info("")
    logger.info(f"✓ Total papers exported: {export.total_papers}")
    logger.info(f"✓ Total author entries: {export.total_authors}")
    logger.info(f"✓ Unique authors: {export.unique_authors}")
    if export.total_papers > 0:
        logger.info(f"✓ Average authors per paper: {export.total_authors / export.total_papers:.1f}")
    if export.unique_authors > 0:
        logger.info(f"✓ Average papers per author: {export.total_authors / export.unique_authors:.2f}")

    logger.info("")
    logger.info("-" * 80)
    logger.info("TRACK NAME MAPPING")
    logger.info("-" * 80)
    for track in export.tracks:
        logger.info(f"  {track.original_name}")
        logger.info(f"    → {track.section_name} ({track.paper_count} paper{'s' if track.paper_count != 1 else ''})")

    logger.info("")
    logger.info("-" * 80)
    logger.info("PAPERS BY SECTION")
    logger.info("-" * 80)
    for section, count in sorted(
        export.papers_by_track.items(), key=lambda x: x[1], reverse=True
    ):
        logger.info(f"  {section}: {count}")

    # Print validation issues
    logger.info("")
    logger.info("-" * 80)
    logger.info("DATA QUALITY")
    logger.info("-" * 80)

    # Count issues by severity
    info_count = sum(1 for i in export.validation_issues if i.severity == "info")

    if export.has_errors:
        logger.error(f"  ✗ {export.error_count} error(s) found")
    if export.has_warnings:
        logger.warning(f"  ⚠ {export.warning_count} warning(s) found")
    if info_count > 0:
        logger.info(f"  ℹ {info_count} informational notice(s)")

    if not export.has_errors and not export.has_warnings:
        logger.info("  ✓ No critical data quality issues detected")
        if info_count > 0:
            logger.info("  → Some informational notices present (see log for details)")
    else:
        # Group issues by category
        issues_by_category = {}
        for issue in export.validation_issues:
            if issue.category not in issues_by_category:
                issues_by_category[issue.category] = []
            issues_by_category[issue.category].append(issue)

        for category, issues in sorted(issues_by_category.items()):
            severity_counts = {}
            for issue in issues:
                severity_counts[issue.severity] = severity_counts.get(issue.severity, 0) + 1

            severity_str = ", ".join(f"{count} {sev}" for sev, count in severity_counts.items())
            logger.info(f"  • {category}: {len(issues)} ({severity_str})")

        logger.info(f"  → Check log file for complete details")

        # Print first few issues at DEBUG level
        logger.debug("")
        logger.debug("=" * 80)
        logger.debug("VALIDATION ISSUES DETAILS")
        logger.debug("=" * 80)
        logger.debug("")
        logger.debug("Note: 'info' level issues are informational and often legitimate")
        logger.debug("      'warning' level issues may need review")
        logger.debug("      'error' level issues must be fixed")
        logger.debug("")
        for issue in export.validation_issues[:20]:
            logger.debug(str(issue))
            if issue.details:
                for key, value in issue.details.items():
                    logger.debug(f"  {key}: {value}")
            logger.debug("")
        if len(export.validation_issues) > 20:
            logger.debug(f"... and {len(export.validation_issues) - 20} more issues")

    logger.info("")
    logger.info("=" * 80)
