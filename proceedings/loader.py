"""
EasyChair Data Loader with Validation
=====================================

Loads an EasyChair export into validated Pydantic models. Two inputs are
accepted and give identical results:

- the Excel workbook (Data → Export → Excel) with 'Submissions' and 'Authors' sheets
- the CSV pair (Submissions → Download): submission.csv + author.csv

Usage:
    from proceedings.loader import load_easychair_data

    export = load_easychair_data(
        "export.xlsx",                           # or ("submission.csv", "author.csv")
        config,                                  # proceedings.config.ConferenceConfig
        submission_date_override="22-JAN-2027",  # Optional
        approval_date_override="02-APR-2027",    # Optional
        section_column="Paper type"              # Optional: column for ACM section tag
    )
"""

import json
import pandas as pd
from pathlib import Path
from typing import Optional, Dict, List, Sequence, Tuple, Union
import logging
from collections import defaultdict
from datetime import datetime

from pydantic import ValidationError

from .config import ConferenceConfig
from .models import (
    Author, Paper, Track, ProceedingsExport, ValidationIssue,
    validate_proceedings_export
)

Source = Union[str, Path, Sequence[Union[str, Path]]]

# Lower-cased EasyChair header (Excel or CSV variant) → canonical column name
SUBMISSION_COLUMNS = {
    "#": "#",
    "id": "#",
    "track name": "Track name",
    "track": "Track name",
    "title": "Title",
    "authors": "Authors",
    "submitted": "Submitted",
    "submission date": "Submitted",
    "last updated": "Last updated",
    "updated": "Last updated",
    "form fields": "Form fields",
    "keywords": "Keywords",
    "decision": "Decision",
    "abstract": "Abstract",
    "approval date": "Approval date",
}

AUTHOR_COLUMNS = {
    "submission #": "Submission #",
    "first name": "First name",
    "last name": "Last name",
    "email": "Email",
    "country": "Country",
    "affiliation": "Affiliation",
    "organization": "Affiliation",
    "organisation": "Affiliation",
    "institution": "Affiliation",
    "web page": "Web page",
    "person #": "Person #",
    "corresponding?": "Corresponding?",
    "corresponding author": "Corresponding?",
    "corresponding": "Corresponding?",
}

# Values EasyChair uses to mark a corresponding author
CORRESPONDING_MARKS = {"✔", "✓", "yes", "y", "true", "1", "x"}


def clean_text(x) -> str:
    """Remove line feeds, tabs, and extra whitespace."""
    if pd.isna(x):
        return ""
    return " ".join(str(x).split())


def _normalize_columns(df: pd.DataFrame, mapping: Dict[str, str]) -> pd.DataFrame:
    """Rename known headers to canonical names; leave other columns untouched."""
    renames = {}
    for col in df.columns:
        canonical = mapping.get(str(col).strip().lower())
        if canonical and canonical not in renames.values() and canonical not in df.columns.drop(col):
            renames[col] = canonical
    return df.rename(columns=renames)


def _read_csv(path: Union[str, Path]) -> pd.DataFrame:
    """Read an EasyChair CSV, falling back to mac_roman when it is not UTF-8."""
    try:
        return pd.read_csv(path, encoding="utf-8-sig", dtype=str, keep_default_na=False)
    except UnicodeDecodeError:
        return pd.read_csv(path, encoding="mac_roman", dtype=str, keep_default_na=False)


def read_easychair(source: Source) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Read an EasyChair export into (submissions_df, authors_df) with canonical
    column names.

    Args:
        source: path to the Excel workbook, or a (submission.csv, author.csv) pair

    Raises:
        FileNotFoundError: If an input file is missing
        ValueError: If the input is not one of the supported shapes
    """
    if isinstance(source, (str, Path)):
        path = Path(source)
        if not path.exists():
            raise FileNotFoundError(f"EasyChair export not found: {path}")
        if path.suffix.lower() not in (".xlsx", ".xls"):
            raise ValueError(
                f"{path.name}: expected an Excel workbook, or a (submission.csv, author.csv) pair"
            )
        excel = pd.ExcelFile(path)
        try:
            submissions_df = pd.read_excel(excel, "Submissions")
            authors_df = pd.read_excel(excel, "Authors")
        except ValueError as e:
            raise ValueError(f"Error reading Excel sheets: {e}")
    else:
        paths = [Path(p) for p in source]
        if len(paths) != 2:
            raise ValueError("Expected exactly two CSV files: submission.csv and author.csv")
        for path in paths:
            if not path.exists():
                raise FileNotFoundError(f"EasyChair export not found: {path}")
        submissions_df, authors_df = _read_csv(paths[0]), _read_csv(paths[1])

    submissions_df = _normalize_columns(submissions_df, SUBMISSION_COLUMNS)
    authors_df = _normalize_columns(authors_df, AUTHOR_COLUMNS)
    # Some author CSVs label the submission number plain '#'
    if "Submission #" not in authors_df.columns and "#" in authors_df.columns:
        authors_df = authors_df.rename(columns={"#": "Submission #"})

    for name, df, required in (
        ("Submissions", submissions_df, ["#", "Title", "Decision"]),
        ("Authors", authors_df, ["Submission #", "First name", "Last name"]),
    ):
        missing = [c for c in required if c not in df.columns]
        if missing:
            raise KeyError(f"{name} data is missing columns {missing}. Found: {list(df.columns)}")

    submissions_df["#"] = pd.to_numeric(submissions_df["#"], errors="coerce")
    submissions_df = submissions_df.dropna(subset=["#"])
    submissions_df["#"] = submissions_df["#"].astype(int)
    authors_df["Submission #"] = pd.to_numeric(authors_df["Submission #"], errors="coerce")
    authors_df = authors_df.dropna(subset=["Submission #"])
    authors_df["Submission #"] = authors_df["Submission #"].astype(int)

    for col in ("Email", "Affiliation", "Country", "Web page", "Corresponding?"):
        if col not in authors_df.columns:
            authors_df[col] = ""

    return submissions_df.reset_index(drop=True), authors_df.reset_index(drop=True)


def load_affiliation_mapping(path: Union[str, Path]) -> Dict[str, str]:
    """
    Load affiliation canonicalisation from JSON shaped {"affiliations": {...}}
    (same file as scan_referees.py --mappings). Keys match case-insensitively.
    """
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return {k.strip().lower(): v for k, v in (data.get("affiliations") or {}).items()}


def apply_affiliation_mapping(
    authors_df: pd.DataFrame,
    mapping: Dict[str, str],
    export: ProceedingsExport,
) -> pd.Series:
    """Replace whole affiliation strings found in mapping; record each change."""
    def canonical(row):
        value = row["Affiliation"]
        new = mapping.get(value.strip().lower(), value) if value else value
        if new != value:
            export.add_issue(
                "info",
                "affiliation_canonicalised",
                f"'{value}' → '{new}'",
                paper_id=int(row["Submission #"]),
                author_name=f"{row['First name']} {row['Last name']}",
            )
        return new
    return authors_df.apply(canonical, axis=1)


def parse_acm_date(date_str: str) -> datetime:
    """
    Parse ACM date format (DD-MON-YYYY) to datetime object.

    Args:
        date_str: Date string in ACM format (e.g., "22-JAN-2026")

    Returns:
        datetime object

    Raises:
        ValueError: If date string format is invalid
    """
    try:
        return datetime.strptime(date_str, "%d-%b-%Y")
    except ValueError:
        raise ValueError(
            f"Invalid date format: '{date_str}'. "
            "Expected format: DD-MON-YYYY (e.g., '22-JAN-2026')"
        )


def parse_authors_from_string(authors_str: str) -> List[str]:
    """
    Parse author names from the Submissions.Authors column.

    Args:
        authors_str: Raw author string (e.g., "John Doe, Jane Smith and Bob Lee")

    Returns:
        List of author names in order
    """
    authors_str = clean_text(authors_str)
    authors_str = authors_str.replace(" and ", ", ")
    return [name.strip() for name in authors_str.split(",") if name.strip()]


def accepted_submissions(submissions_df: pd.DataFrame, config: ConferenceConfig) -> pd.DataFrame:
    """Rows whose decision is in config.accepted_decisions (case-insensitive)."""
    return submissions_df[submissions_df["Decision"].map(config.is_accepted)]


def decision_breakdown(submissions_df: pd.DataFrame) -> Dict[str, int]:
    """Count of submissions per EasyChair decision (blank → '(no decision)')."""
    decisions = submissions_df["Decision"].map(lambda d: clean_text(d) or "(no decision)")
    return dict(sorted(decisions.value_counts().items()))


def load_easychair_data(
    source: Source,
    config: ConferenceConfig,
    track_filter: Optional[str] = None,
    paper_id_filter: Optional[int] = None,
    proceeding_id: Optional[str] = None,
    submission_date_override: Optional[str] = None,
    approval_date_override: Optional[str] = None,
    section_column: Optional[str] = None,
    affiliation_mapping: Optional[Dict[str, str]] = None,
    logger: Optional[logging.Logger] = None
) -> ProceedingsExport:
    """
    Load and validate EasyChair export data.

    Args:
        source: Excel workbook path, or (submission.csv, author.csv) pair
        config: Conference settings (accepted decisions, categories, paper types)
        track_filter: Optional track name to filter
        paper_id_filter: Optional paper ID to filter (submission number)
        proceeding_id: Optional ACM proceeding ID
        submission_date_override: Optional submission date to use for all papers (e.g., '22-JAN-2026')
        approval_date_override: Optional approval date to use for all papers (e.g., '02-APR-2026')
        section_column: Optional column name to use for ACM section tag (e.g., 'Paper type')
        affiliation_mapping: Optional {lower-cased affiliation: canonical name} map
            (see load_affiliation_mapping); off by default because it changes
            what authors typed, and that is what TAPS prints
        logger: Optional logger instance

    Returns:
        Validated ProceedingsExport object

    Raises:
        ValueError: If required data is invalid
        FileNotFoundError: If an input file is not found
        KeyError: If required columns are missing
    """
    if logger is None:
        logger = logging.getLogger(__name__)

    # Parse date overrides if provided
    submission_date_dt = None
    approval_date_dt = None

    if submission_date_override:
        try:
            submission_date_dt = parse_acm_date(submission_date_override)
            logger.info(f"Using submission date override: {submission_date_override}")
        except ValueError as e:
            raise ValueError(f"Invalid submission date: {e}")

    if approval_date_override:
        try:
            approval_date_dt = parse_acm_date(approval_date_override)
            logger.info(f"Using approval date override: {approval_date_override}")
        except ValueError as e:
            raise ValueError(f"Invalid approval date: {e}")

    # Initialize export object
    export = ProceedingsExport(proceeding_id=proceeding_id, conference_name=config.label)

    logger.info(f"Loading EasyChair export: {source}")
    submissions_df, authors_df = read_easychair(source)

    logger.info(
        f"Loaded {len(submissions_df)} submissions and {len(authors_df)} author records"
    )

    # Validate section_column if provided
    if section_column:
        if section_column not in submissions_df.columns:
            available_cols = ", ".join(map(str, submissions_df.columns[:10]))
            raise ValueError(
                f"Section column '{section_column}' not found in Submissions sheet. "
                f"Available columns: {available_cols}..."
            )
        logger.info(f"Using column '{section_column}' for ACM section tag")
    else:
        logger.info("No section column specified - section tags will be empty")

    if approval_date_dt is None and "Approval date" not in submissions_df.columns:
        export.add_issue(
            "warning",
            "missing_approval_date",
            "The EasyChair export has no approval date; set the approval date override "
            "(the notification date, DD-MON-YYYY)",
        )

    # Filter by track if specified
    if track_filter:
        submissions_df = submissions_df[submissions_df["Track name"] == track_filter]
        logger.info(f"Filtered to {len(submissions_df)} submissions in track: {track_filter}")

    # Filter by paper ID if specified
    if paper_id_filter is not None:
        submissions_df = submissions_df[submissions_df["#"] == paper_id_filter]
        if len(submissions_df) == 0:
            raise ValueError(f"Paper ID {paper_id_filter} not found in EasyChair export")
        logger.info(f"Filtered to paper ID: {paper_id_filter}")

    # Filter for accepted papers only
    export.decision_counts = decision_breakdown(submissions_df)
    submissions_df = accepted_submissions(submissions_df, config).copy()
    logger.info(f"Found {len(submissions_df)} accepted submissions")

    if len(submissions_df) == 0:
        logger.warning("No accepted submissions found! Check the accepted decisions in the config.")
        return export

    # Clean text fields
    submissions_df["Title"] = submissions_df["Title"].map(clean_text)
    if "Track name" in submissions_df.columns:
        submissions_df["Track name"] = submissions_df["Track name"].map(clean_text)
    if "Keywords" in submissions_df.columns:
        submissions_df["Keywords"] = submissions_df["Keywords"].map(
            lambda x: "; ".join(str(x).split("\n")) if pd.notna(x) and x else ""
        )

    authors_df["First name"] = authors_df["First name"].map(clean_text)
    authors_df["Last name"] = authors_df["Last name"].map(clean_text)
    authors_df["Email"] = authors_df["Email"].map(
        lambda x: str(x).strip() if pd.notna(x) else ""
    )
    authors_df["Affiliation"] = authors_df["Affiliation"].map(clean_text)
    authors_df["Country"] = authors_df["Country"].map(clean_text)
    if affiliation_mapping:
        authors_df["Affiliation"] = apply_affiliation_mapping(authors_df, affiliation_mapping, export)

    # Consolidate duplicate author entries
    logger.info("Consolidating duplicate author entries...")
    authors_df = consolidate_duplicate_authors(authors_df, logger)

    # Group papers by paper type
    papers_by_type: Dict[str, List[Paper]] = defaultdict(list)
    track_names_by_type: Dict[str, List[str]] = defaultdict(list)

    # Process each submission
    for _, submission in submissions_df.iterrows():
        try:
            paper = load_paper_from_submission(
                submission,
                authors_df,
                config,
                export,
                logger,
                submission_date_override=submission_date_dt,
                approval_date_override=approval_date_dt,
                section_column=section_column
            )
            if paper:
                papers_by_type[paper.paper_type].append(paper)
                if paper.track_name not in track_names_by_type[paper.paper_type]:
                    track_names_by_type[paper.paper_type].append(paper.track_name)
        except Exception as e:
            logger.error(f"Error loading paper #{submission['#']}: {e}")
            export.add_issue(
                "error",
                "loading_error",
                f"Failed to load paper: {str(e)}",
                paper_id=submission['#']
            )

    # Create Track objects, one per paper type, in proceedings order
    for paper_type in sorted(papers_by_type, key=config.type_order):
        track = Track(
            original_name="; ".join(t for t in track_names_by_type[paper_type] if t),
            section_name=paper_type,
            papers=sorted(papers_by_type[paper_type], key=lambda p: p.submission_id)
        )
        export.tracks.append(track)

    # Run validation
    logger.info("Running validation...")
    export = validate_proceedings_export(export)

    logger.info(f"Loaded {export.total_papers} papers across {len(export.tracks)} paper types")
    logger.info(f"Total authors: {export.total_authors}, Unique: {export.unique_authors}")

    if export.has_errors:
        logger.error(f"Found {export.error_count} error(s)")
    if export.has_warnings:
        logger.warning(f"Found {export.warning_count} warning(s)")

    return export


def consolidate_duplicate_authors(
    authors_df: pd.DataFrame,
    logger: logging.Logger
) -> pd.DataFrame:
    """
    Fill missing fields for the same author across different papers.

    This function identifies the same person across multiple papers (by name + email)
    and fills ONLY EMPTY fields. It NEVER overwrites existing values, allowing authors
    to legitimately have different affiliations/emails/countries for different papers.

    Example:
    - Paper 1: John Doe (john@mit.edu), affiliation="MIT", country="USA"
    - Paper 2: John Doe (john@mit.edu), affiliation="", country=""
    → Paper 2 gets filled: affiliation="MIT", country="USA"

    - Paper 3: John Doe (john@mit.edu), affiliation="Stanford", country="USA"
    → Paper 3 is NOT changed (existing affiliation is kept)

    Args:
        authors_df: DataFrame with author data
        logger: Logger instance

    Returns:
        Cleaned DataFrame with missing fields filled
    """
    author_corrections = 0

    def get_author_key(row):
        """
        Create a unique key for identifying the same person across papers.
        Uses name + email to identify individuals.
        """
        email = (
            row["Email"].lower().strip()
            if pd.notna(row["Email"]) and row["Email"] and row["Email"] != "nan"
            else ""
        )
        return (
            row["First name"].lower().strip(),
            row["Last name"].lower().strip(),
            email,
        )

    def is_empty_value(val):
        """Check if a field value is empty/missing."""
        return pd.isna(val) or not str(val).strip() or str(val) == "nan"

    # Group by author identity (across all papers)
    authors_df["_author_key"] = authors_df.apply(get_author_key, axis=1)

    # For each unique author, collect all non-empty values for each field
    # We'll use the first non-empty value found
    consolidated_info = {}

    for author_key, group in authors_df.groupby("_author_key"):
        if len(group) > 1:
            # Author appears in multiple papers
            info = {}
            for field in ["Email", "Country", "Web page", "Affiliation"]:
                # Find first non-empty value for this field
                best_val = ""
                for _, row in group.iterrows():
                    val = row.get(field, "")
                    if not is_empty_value(val):
                        best_val = val
                        break  # Use first non-empty value found
                info[field] = best_val
            consolidated_info[author_key] = info

    # Apply consolidated info ONLY to empty fields (never overwrite)
    for idx, row in authors_df.iterrows():
        key = row["_author_key"]
        if key in consolidated_info:
            for field, value in consolidated_info[key].items():
                old_val = row.get(field, "")
                # Only fill if current value is empty AND we have a value to fill
                if is_empty_value(old_val) and value:
                    logger.debug(
                        f"Filling {field} for {row['First name']} {row['Last name']} "
                        f"(Paper #{row['Submission #']}): '{old_val}' → '{value}'"
                    )
                    authors_df.at[idx, field] = value
                    author_corrections += 1

    authors_df = authors_df.drop(columns=["_author_key"])

    if author_corrections > 0:
        logger.info(f"Made {author_corrections} field correction(s) by filling empty fields across papers")
        logger.info("Note: Existing values were never overwritten (authors can have different affiliations per paper)")
    else:
        logger.info("No empty author fields to fill from other papers")

    return authors_df



def _optional_str(value) -> Optional[str]:
    if value is None or pd.isna(value):
        return None
    value = str(value).strip()
    return value or None


def _parse_date(value) -> Optional[datetime]:
    if value is None or pd.isna(value) or not str(value).strip():
        return None
    try:
        return pd.to_datetime(value).to_pydatetime()
    except (ValueError, TypeError):
        return None


def build_author(
    author_row: pd.Series,
    submission_id: int,
    export: ProceedingsExport,
) -> Author:
    """
    Create an Author from an Authors row. An invalid email never drops the
    author: the email is left blank and a warning is recorded instead.
    """
    person_id = pd.to_numeric(author_row.get("Person #"), errors="coerce")
    fields = dict(
        first_name=str(author_row.get("First name", "")),
        last_name=str(author_row.get("Last name", "")),
        email=_optional_str(author_row.get("Email")),
        affiliation=_optional_str(author_row.get("Affiliation")),
        country=_optional_str(author_row.get("Country")),
        web_page=_optional_str(author_row.get("Web page")),
        is_corresponding=str(author_row.get("Corresponding?", "")).strip().lower() in CORRESPONDING_MARKS,
        person_id=int(person_id) if pd.notna(person_id) else None,
    )
    try:
        return Author(**fields)
    except ValidationError as e:
        if fields["email"] and any(err["loc"] == ("email",) for err in e.errors()):
            export.add_issue(
                "warning",
                "invalid_email",
                f"Invalid email '{fields['email']}' left blank",
                paper_id=submission_id,
                author_name=f"{fields['first_name']} {fields['last_name']}",
            )
            fields["email"] = None
            return Author(**fields)
        raise


def load_paper_from_submission(
    submission: pd.Series,
    authors_df: pd.DataFrame,
    config: ConferenceConfig,
    export: ProceedingsExport,
    logger: logging.Logger,
    submission_date_override: Optional[datetime] = None,
    approval_date_override: Optional[datetime] = None,
    section_column: Optional[str] = None
) -> Optional[Paper]:
    """
    Load a single paper from submission data.

    Args:
        submission: Submission row from DataFrame
        authors_df: Authors DataFrame
        config: Conference settings (categorisation rules, paper types)
        export: Export object to add issues to
        logger: Logger instance
        submission_date_override: Optional override for submission date (all papers)
        approval_date_override: Optional override for approval date (all papers)
        section_column: Optional column name to use for ACM section tag

    Returns:
        Paper object or None if loading fails
    """
    submission_id = int(submission["#"])
    track_name = clean_text(submission.get("Track name", ""))

    # Paper type from the configured categorisation rules
    paper_type = config.categorize(submission)
    if paper_type is None:
        form_fields = clean_text(submission.get("Form fields", ""))
        logger.error(
            f"Paper #{submission_id} accepted but not categorised "
            f"(track: '{track_name}', form fields: '{form_fields}')"
        )
        export.add_issue(
            "error",
            "uncategorised",
            "Accepted but no category rule matched; add a rule or fix the paper in EasyChair",
            paper_id=submission_id,
            track=track_name,
            form_fields=form_fields,
        )
        return None

    # Section name: use specified column if provided, otherwise empty
    if section_column:
        section_name = clean_text(submission.get(section_column, ""))
    else:
        section_name = ""

    # Get all authors for this paper from Authors sheet
    paper_authors_df = authors_df[authors_df["Submission #"] == submission_id]

    if len(paper_authors_df) == 0:
        logger.error(f"No authors found for submission #{submission_id}")
        export.add_issue(
            "error",
            "no_authors",
            "Paper has no authors",
            paper_id=submission_id
        )
        return None

    # Get expected author order from Submissions.Authors column
    authors_str = submission.get("Authors", "")
    expected_order = parse_authors_from_string(authors_str) if pd.notna(authors_str) else []
    if not expected_order:
        export.add_issue(
            "info",
            "author_order_from_rows",
            "No 'Authors' column; author order taken from the author rows",
            paper_id=submission_id
        )

    # Create name-to-position mapping
    name_to_position = {}
    for idx, name in enumerate(expected_order):
        name_to_position[name.lower()] = idx

    # Build Author objects in correct order
    authors_with_sequence = []
    for row_index, (_, author_row) in enumerate(paper_authors_df.iterrows()):
        try:
            author = build_author(author_row, submission_id, export)

            # Determine sequence
            full_name = author.full_name.lower()
            if not expected_order:
                sequence = row_index
            elif full_name in name_to_position:
                sequence = name_to_position[full_name]
            else:
                # Try partial match
                sequence = None
                for correct_name, pos in name_to_position.items():
                    if full_name in correct_name or correct_name in full_name:
                        sequence = pos
                        break

                if sequence is None:
                    # Name mismatch
                    logger.warning(
                        f"Author name mismatch in Paper #{submission_id}: "
                        f"'{author.full_name}' from Authors sheet not found in Submissions.Authors"
                    )
                    export.add_issue(
                        "warning",
                        "author_order_mismatch",
                        f"Author '{author.full_name}' not found in expected order",
                        paper_id=submission_id,
                        author_name=author.full_name
                    )
                    sequence = 1000 + row_index  # Put at end

            authors_with_sequence.append((sequence, author))

        except Exception as e:
            logger.error(f"Error creating author for paper #{submission_id}: {e}")
            export.add_issue(
                "error",
                "author_validation_error",
                f"Failed to validate author: {str(e)}",
                paper_id=submission_id
            )
            continue

    # Sort by sequence
    authors_with_sequence.sort(key=lambda x: x[0])
    authors = [author for _, author in authors_with_sequence]

    if not authors:
        logger.error(f"No valid authors for submission #{submission_id}")
        return None

    # Helper to check valid email
    def has_valid_email(author):
        return author.email is not None and author.email.strip() != ""

    # Determine contact author priority BEFORE Paper validation modifies flags
    marked_corresponding = [a for a in authors if a.is_corresponding]
    marked_corresponding_with_email = [a for a in marked_corresponding if has_valid_email(a)]
    has_priority_1 = len(marked_corresponding_with_email) > 0

    # Parse dates - use overrides if provided, otherwise read from the export
    if submission_date_override is not None:
        submitted_date = submission_date_override
    else:
        submitted_date = _parse_date(submission.get("Submitted"))

    if approval_date_override is not None:
        approval_date = approval_date_override
    else:
        approval_date = _parse_date(submission.get("Approval date"))

    # Create Paper object (will validate and set contact author)
    try:
        paper = Paper(
            submission_id=submission_id,
            title=str(submission.get("Title", "")),
            authors=authors,
            track_name=track_name,
            section_name=section_name,
            paper_type=paper_type,
            event_tracking_number=f"{config.prefix_for(paper_type)}{submission_id}",
            keywords=_optional_str(submission.get("Keywords")),
            abstract=clean_text(submission.get("Abstract", "")) or None,
            submitted_date=submitted_date,
            approval_date=approval_date,
        )

        # Several people marked corresponding: only the first one (with an
        # email) gets the ACM emails. Record it so the chair knows who that is.
        if len(marked_corresponding) > 1:
            contact = paper.corresponding_authors[0]
            names = ", ".join(a.full_name for a in marked_corresponding)
            export.add_issue(
                "warning",
                "multiple_corresponding",
                f"{len(marked_corresponding)} authors marked corresponding ({names}); "
                f"contact author will be {contact.full_name} <{contact.email or 'no email'}>",
                paper_id=submission_id,
                author_name=contact.full_name,
            )

        # Log contact author selection priority if not priority 1
        if not has_priority_1:
            contact_author = paper.corresponding_authors[0] if paper.corresponding_authors else None
            if contact_author:
                # Contact author is first author (either priority 2 or 3)
                if has_valid_email(contact_author):
                    # Priority 2: First author with valid email
                    logger.warning(
                        f"⚠ Paper #{submission_id} ('{paper.title[:60]}...'): "
                        f"No corresponding author marked or no valid email. Using first author with valid email as contact author."
                    )
                    export.add_issue(
                        "warning",
                        "contact_author_priority_2",
                        "Using first author with valid email as contact author (no corresponding author marked with valid email)",
                        paper_id=submission_id
                    )
                else:
                    # Priority 3: First author without valid email
                    logger.error(
                        f"✗ Paper #{submission_id} ('{paper.title[:60]}...'): "
                        f"No valid emails found. Using first author '{contact_author.full_name}' "
                        f"as contact author despite invalid/missing email."
                    )
                    export.add_issue(
                        "error",
                        "contact_author_priority_3",
                        f"Using first author '{contact_author.full_name}' as contact author despite invalid/missing email",
                        paper_id=submission_id
                    )

        return paper
    except Exception as e:
        logger.error(f"Error creating paper #{submission_id}: {e}")
        export.add_issue(
            "error",
            "paper_validation_error",
            f"Failed to validate paper: {str(e)}",
            paper_id=submission_id
        )
        return None
