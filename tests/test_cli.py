"""Regression tests for easychair_export.py."""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).parent / "fixtures"))

import easychair_export  # noqa: E402
from make_fixtures import write_fixtures  # noqa: E402

CONFIG = str(Path(__file__).parent / "fixtures" / "chiir2027.json")


@pytest.mark.parametrize("output", [str(ROOT), str(ROOT / "out"), "."])
def test_output_inside_repository_is_refused(output, tmp_path, monkeypatch):
    monkeypatch.chdir(ROOT)
    files = write_fixtures(tmp_path)
    with pytest.raises(SystemExit) as exit_info:
        easychair_export.main(["--config", CONFIG, "--input", str(files["xlsx"]), "--format", "csv",
                               "--event_id", "1234567", "--output", output])
    assert exit_info.value.code == 2
    assert not (ROOT / "out").exists() and not list(ROOT.glob("CHIIR-*.csv"))


def test_output_is_required(tmp_path):
    files = write_fixtures(tmp_path)
    with pytest.raises(SystemExit):
        easychair_export.main(["--config", CONFIG, "--input", str(files["xlsx"]), "--format", "csv",
                               "--event_id", "1234567"])


def test_output_outside_repository_is_written(tmp_path):
    files = write_fixtures(tmp_path / "data")
    out = tmp_path / "output"
    easychair_export.main(["--config", CONFIG, "--input", str(files["xlsx"]), "--format", "csv",
                           "--event_id", "1234567", "--output", str(out)])
    assert (out / "CHIIR-2027-All-Papers.csv").exists()
