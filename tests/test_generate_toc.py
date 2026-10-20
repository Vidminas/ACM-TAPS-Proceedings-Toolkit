"""Regression tests for generate_toc.py."""

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from generate_toc import generate_toc  # noqa: E402


def taps_export(tmp_path, rows):
    path = tmp_path / "ExportMetadata.xlsx"
    pd.DataFrame(rows).to_excel(path, index=False)
    return str(path)


def row(order, first_author, pages, other="A Author!~!X"):
    return {"ORDER ID": order, "PAPER TYPE": "Full Paper", "TITLE": f"Paper {order}",
            "FIRST AUTHOR": first_author, "OTHER AUTHORS": other, "PDFPAGES": pages}


def test_blank_first_author_is_not_nan(tmp_path):
    _, toc = generate_toc(taps_export(tmp_path, [row(1, None, 10)]), str(tmp_path / "toc"))
    assert list(toc["Authors"]) == ["A Author"]


def test_blank_page_count_names_the_paper(tmp_path):
    path = taps_export(tmp_path, [row(1, "B", 10), row(2, "C", None)])
    with pytest.raises(ValueError, match="Paper 2"):
        generate_toc(path, str(tmp_path / "toc"))
