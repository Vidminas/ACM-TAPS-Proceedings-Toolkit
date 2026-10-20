"""Text helpers shared by the exporters and the validation package."""

from typing import Optional


def clean_affiliation_string(affiliation_str: Optional[str]) -> str:
    """
    Strip whitespace and leading/trailing punctuation from an affiliation.

    Handles common data quality issues like:
    - ", Tsinghua University" → "Tsinghua University"
    - "MIT, " → "MIT"
    - " , Stanford University" → "Stanford University"

    Args:
        affiliation_str: Raw affiliation string

    Returns:
        str: Cleaned affiliation string ("" for None or empty input)
    """
    if not affiliation_str:
        return ""

    cleaned = affiliation_str.strip()

    # Keep stripping until no more leading/trailing punctuation+whitespace
    while cleaned and cleaned[0] in '.,;:-_':
        cleaned = cleaned[1:].strip()
    while cleaned and cleaned[-1] in '.,;:-_':
        cleaned = cleaned[:-1].strip()

    return cleaned
