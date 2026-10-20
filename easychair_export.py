"""
EasyChair → ACM eRights CSV / ACM XML / lists / heading preview
================================================================

Command-line version of steps 3–7 of the runbook notebook
(chiir2027_proceedings.ipynb). The notebook's last cell saves the settings as
JSON for --config, so the same run can be repeated headlessly.

Input is either the EasyChair Excel workbook (Data → Export → Excel) or the
CSV pair (submission.csv author.csv).

Usage:
    # eRights CSV files (one per paper type + combined) for upload
    python easychair_export.py --config chiir2027.json --input submission.csv author.csv \\
        --format csv --event_id 1234567 --output out/

    # ACM/Sheridan XML
    python easychair_export.py --config chiir2027.json --input export.xlsx \\
        --format xml --proceeding_id 2027-CHIIR --output out/chiir2027.xml

    # Heading preview to send to authors before eRights
    python easychair_export.py --config chiir2027.json --input export.xlsx \\
        --format preview --output out/headings.txt

    # Re-issue one paper after it was removed from TAPS/eRights
    python easychair_export.py --config chiir2027.json --input export.xlsx \\
        --format csv --event_id 1234567 --paper_id 42 --output out/reissue-42/
"""

import argparse
import logging
import sys
from pathlib import Path

from proceedings.config import ConferenceConfig
from proceedings.crosscheck import check_erights_csv, check_xml_against_source
from proceedings.exporters import (
    export_preview,
    export_to_erights_csv,
    export_to_text,
    export_to_xml,
    print_summary,
)
from proceedings.loader import load_affiliation_mapping, load_easychair_data


def setup_logging(log_file: str) -> logging.Logger:
    """
    Set up logging to both console and file.

    Console: INFO level and above
    File: All levels including DEBUG

    Args:
        log_file: Path to log file

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger("easychair_to_acm")
    logger.setLevel(logging.DEBUG)

    # Clear existing handlers
    if logger.handlers:
        logger.handlers.clear()

    # Console handler - INFO and above
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter("%(message)s"))

    # File handler - DEBUG and above
    file_handler = logging.FileHandler(log_file, mode="w", encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger


def report_crosscheck(problems, logger: logging.Logger) -> bool:
    """Log cross-check results; return True if they passed."""
    logger.info("")
    logger.info("=" * 80)
    logger.info("CROSS-CHECK AGAINST EASYCHAIR EXPORT")
    logger.info("=" * 80)
    if not problems:
        logger.info("✓ Output matches the EasyChair export")
        return True
    for problem in problems:
        logger.error(f"  ✗ {problem}")
    return False


def main(argv=None):
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Convert an EasyChair export to ACM eRights CSV, ACM XML, text/markdown lists or a heading preview",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__.split("Usage:")[1],
    )
    parser.add_argument("--config", required=True, metavar="JSON",
                        help="Conference settings saved from the runbook notebook")
    parser.add_argument("--input", required=True, nargs="+", metavar="FILE",
                        help="EasyChair Excel workbook, or submission.csv author.csv")
    parser.add_argument("--format", choices=["csv", "xml", "txt", "md", "preview"], default="csv",
                        help="Output format (default: csv)")
    parser.add_argument("--output", default=None, metavar="PATH",
                        help="Output file (xml/txt/md/preview) or folder (csv). Default: acm_output.<format> / ./")
    parser.add_argument("--event_id", metavar="ID",
                        help="ACM event ID from the eRights confirmation email (required for csv)")
    parser.add_argument("--proceeding_id", metavar="ID",
                        help="ACM proceeding ID, e.g. '2027-CHIIR' (required for xml)")
    parser.add_argument("--source", default="EasyChair",
                        help="Source system name for XML metadata (default: 'EasyChair')")
    parser.add_argument("--track", default=None, metavar="NAME",
                        help="Export ONLY papers from this EasyChair track (exact, case-sensitive)")
    parser.add_argument("--paper_id", type=int, default=None, metavar="ID",
                        help="Export ONLY this submission number (for re-issuing one paper)")
    parser.add_argument("--submission_date", default=None, metavar="DATE",
                        help="Override submission date for all papers, e.g. '22-OCT-2026'")
    parser.add_argument("--approval_date", default=None, metavar="DATE",
                        help="Override approval/notification date for all papers, e.g. '01-DEC-2026'")
    parser.add_argument("--section_column", default=None, metavar="COLUMN",
                        help="Submissions column to use for the ACM section tag (default: empty)")
    parser.add_argument("--affiliation_mapping", default=None, metavar="JSON",
                        help="Canonicalise affiliations with this map (e.g. affiliations_mapping.json)")
    parser.add_argument("--no-validation", action="store_true",
                        help="Skip the cross-check against the EasyChair export")
    args = parser.parse_args(argv)

    source = args.input[0] if len(args.input) == 1 else args.input
    if args.format == "csv" and not args.event_id:
        parser.error("--event_id is required for --format csv")
    if args.format == "xml" and not args.proceeding_id:
        parser.error("--proceeding_id is required for --format xml")

    if args.output is None:
        args.output = "." if args.format == "csv" else f"acm_output.{args.format if args.format != 'preview' else 'txt'}"
    if args.format == "csv":
        Path(args.output).mkdir(parents=True, exist_ok=True)
        log_file = str(Path(args.output) / "export.log")
    else:
        expected_ext = ".txt" if args.format == "preview" else f".{args.format}"
        if not args.output.endswith(expected_ext):
            args.output = f"{args.output}{expected_ext}"
        log_file = args.output + ".log"

    logger = setup_logging(log_file)
    config = ConferenceConfig.from_json(args.config)
    mapping = load_affiliation_mapping(args.affiliation_mapping) if args.affiliation_mapping else None

    logger.info("=" * 80)
    logger.info(f"{config.label}: EASYCHAIR TO {args.format.upper()}")
    logger.info("=" * 80)
    logger.info(f"Output: {args.output}")
    logger.info(f"Log file: {log_file}")
    logger.info("")

    try:
        export = load_easychair_data(
            source,
            config,
            track_filter=args.track,
            paper_id_filter=args.paper_id,
            proceeding_id=args.proceeding_id,
            submission_date_override=args.submission_date,
            approval_date_override=args.approval_date,
            section_column=args.section_column,
            affiliation_mapping=mapping,
            logger=logger,
        )

        crosscheck_ok = True
        if args.format == "xml":
            export_to_xml(export, args.output, source=args.source, logger=logger)
            if not args.no_validation:
                paper_ids = [args.paper_id] if args.paper_id is not None else None
                crosscheck_ok = report_crosscheck(
                    check_xml_against_source(source, config, args.output, paper_ids, mapping), logger
                )
        elif args.format == "csv":
            written = export_to_erights_csv(export, args.output, args.event_id, config, logger=logger)
            if not args.no_validation:
                crosscheck_ok = report_crosscheck(
                    [p for path in written.values() for p in check_erights_csv(path)], logger
                )
        elif args.format == "preview":
            export_preview(export, args.output, logger=logger)
        else:
            export_to_text(export, args.output, format_type=args.format, logger=logger)

        print_summary(export, logger)
        logger.info(f"Log file saved to: {log_file}")

        if export.has_errors or not crosscheck_ok:
            logger.error("")
            logger.error("Export completed with errors. Please review the log file.")
            return 1
        if export.has_warnings:
            logger.warning("")
            logger.warning("Export completed with warnings. Please review the log file.")
            return 0
        logger.info("")
        logger.info("Export completed successfully!")
        return 0

    except Exception as e:
        logger.error("")
        logger.error(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
