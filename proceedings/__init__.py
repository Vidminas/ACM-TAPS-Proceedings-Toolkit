"""
ACM proceedings toolkit (EasyChair → ACM eRights/TAPS)
======================================================

Modules:
- config: per-conference settings (decisions, categories, paper types)
- models: Pydantic data models with validation
- loader: reads the EasyChair Excel workbook or CSV pair into the models
- exporters: ACM XML, eRights CSV, TXT/MD lists, heading previews
- crosscheck: checks generated files against the raw EasyChair export
- validation: analysis of ACM XML files (used by validate_acm_xml.py)

Usage:
    from proceedings import ConferenceConfig, load_easychair_data, export_to_xml

    export = load_easychair_data("data.xlsx", config)
    export_to_xml(export, "output.xml")
"""

from .config import CategoryRule, ConferenceConfig, PaperType

from .models import (
    Author,
    Paper,
    Track,
    ProceedingsExport,
    ValidationIssue,
    affiliation_detail_problems,
    validate_author_name_consistency,
    validate_proceedings_export,
)

from .loader import load_affiliation_mapping, load_easychair_data, read_easychair

from .exporters import (
    export_preview,
    export_to_erights_csv,
    export_to_text,
    export_to_xml,
    heading_previews,
    print_summary,
)

from .crosscheck import check_erights_csv, check_xml_against_source

__all__ = [
    # Config
    "CategoryRule",
    "ConferenceConfig",
    "PaperType",
    # Models
    "Author",
    "Paper",
    "Track",
    "ProceedingsExport",
    "ValidationIssue",
    # Validation functions
    "affiliation_detail_problems",
    "validate_author_name_consistency",
    "validate_proceedings_export",
    # Loader
    "load_affiliation_mapping",
    "load_easychair_data",
    "read_easychair",
    # Exporters
    "export_preview",
    "export_to_erights_csv",
    "export_to_text",
    "export_to_xml",
    "heading_previews",
    "print_summary",
    # Cross-checks
    "check_erights_csv",
    "check_xml_against_source",
]

__version__ = "3.0.0"
