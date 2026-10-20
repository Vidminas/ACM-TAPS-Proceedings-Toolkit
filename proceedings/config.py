"""
Conference configuration
========================

Everything that changes from one year (or conference) to the next lives in a
``ConferenceConfig``. The runbook notebook builds it step by step; the CLI
(``easychair_export.py --config``) reads the same structure from JSON.

Usage:
    from proceedings.config import ConferenceConfig, CategoryRule, PaperType

    config = ConferenceConfig(
        name="CHIIR", year=2027,
        accepted_decisions=["accept", "probably accept"],
        paper_types=[PaperType(name="Full Paper", prefix="fp", heading="Full Papers",
                               file_stem="Full-Papers")],
        category_rules=[CategoryRule(field="form fields",
                                     contains=["(category) full paper"],
                                     paper_type="Full Paper")],
    )
"""

import json
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, Field, model_validator


class PaperType(BaseModel):
    """An ACM paper type, in the order it should appear in the proceedings."""
    name: str = Field(..., description="ACM paper type, exactly as uploaded to eRights")
    prefix: str = Field(..., description="Event tracking number prefix, e.g. 'fp' -> fp123")
    heading: Optional[str] = Field(None, description="Section heading for lists/ToC (defaults to name)")
    file_stem: Optional[str] = Field(None, description="Per-type CSV file name part (defaults to name)")

    @property
    def display_heading(self) -> str:
        return self.heading or self.name

    @property
    def csv_stem(self) -> str:
        return self.file_stem or self.name.replace(" ", "-")


class CategoryRule(BaseModel):
    """
    One categorisation rule. Rules are checked in order; the first match wins.

    ``field`` is an EasyChair Submissions column (case-insensitive), e.g.
    'form fields' or 'track name'. The rule matches when the column contains
    ANY of ``contains`` and ALL of ``contains_all`` (case-insensitive).
    """
    field: str
    contains: List[str] = Field(default_factory=list)
    contains_all: List[str] = Field(default_factory=list)
    paper_type: str

    @model_validator(mode="after")
    def needs_a_condition(self):
        if not self.contains and not self.contains_all:
            raise ValueError("CategoryRule needs 'contains' or 'contains_all'")
        return self

    def matches(self, value: str) -> bool:
        value = (value or "").lower()
        if self.contains and not any(s.lower() in value for s in self.contains):
            return False
        return all(s.lower() in value for s in self.contains_all)


class ConferenceConfig(BaseModel):
    """Per-conference settings used by the loader and exporters."""
    name: str = Field(..., description="Conference acronym, e.g. 'CHIIR'")
    year: int
    accepted_decisions: List[str] = Field(..., min_length=1,
                                          description="EasyChair decisions to include (case-insensitive)")
    paper_types: List[PaperType] = Field(..., min_length=1)
    category_rules: List[CategoryRule] = Field(..., min_length=1)

    @model_validator(mode="after")
    def rules_use_known_types(self):
        known = {t.name for t in self.paper_types}
        unknown = sorted({r.paper_type for r in self.category_rules} - known)
        if unknown:
            raise ValueError(f"category_rules refer to undefined paper types: {unknown}")
        return self

    @property
    def label(self) -> str:
        """e.g. 'CHIIR 2027'"""
        return f"{self.name} {self.year}"

    def is_accepted(self, decision) -> bool:
        decision = str(decision or "").strip().lower()
        return decision in {d.strip().lower() for d in self.accepted_decisions}

    def paper_type(self, name: str) -> Optional[PaperType]:
        return next((t for t in self.paper_types if t.name == name), None)

    def type_order(self, name: str) -> int:
        names = [t.name for t in self.paper_types]
        return names.index(name) if name in names else len(names)

    def prefix_for(self, name: str) -> str:
        paper_type = self.paper_type(name)
        return paper_type.prefix if paper_type else "paper"

    def categorize(self, submission) -> Optional[str]:
        """
        Return the paper type for a submission row (dict-like with EasyChair
        column names), or None when no rule matches.
        """
        lowered = {str(k).strip().lower(): v for k, v in dict(submission).items()}
        for rule in self.category_rules:
            value = lowered.get(rule.field.strip().lower())
            if value is None or value != value:  # missing or NaN
                continue
            if rule.matches(str(value)):
                return rule.paper_type
        return None

    @classmethod
    def from_json(cls, path) -> "ConferenceConfig":
        return cls.model_validate(json.loads(Path(path).read_text(encoding="utf-8")))

    def to_json(self, path) -> None:
        Path(path).write_text(self.model_dump_json(indent=2) + "\n", encoding="utf-8")
