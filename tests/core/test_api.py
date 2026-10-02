"""File reads and the public compare_files entry."""

from __future__ import annotations

import os
import re
from pathlib import Path

import pytest

from lupaxa.diff_ini_files import InputError, compare_files


def test_missing_file(tmp_path: Path) -> None:
    """A missing path names the path the caller passed."""
    missing = tmp_path / "missing.ini"
    present = tmp_path / "present.ini"
    present.write_text("[database]\nhost = localhost\n", encoding="utf-8")
    with pytest.raises(InputError, match=f"'{re.escape(str(missing))}' does not exist"):
        compare_files(missing, present)


def test_directory(tmp_path: Path) -> None:
    """A directory is not an INI file."""
    present = tmp_path / "present.ini"
    present.write_text("[database]\nhost = localhost\n", encoding="utf-8")
    with pytest.raises(InputError, match=f"'{re.escape(str(tmp_path))}' is a directory"):
        compare_files(tmp_path, present)


def test_permission_denied(tmp_path: Path) -> None:
    """An unreadable file reports permission denied."""
    if os.geteuid() == 0:
        pytest.skip("root ignores file mode")
    locked = tmp_path / "locked.ini"
    other = tmp_path / "other.ini"
    locked.write_text("[database]\nhost = localhost\n", encoding="utf-8")
    other.write_text("[database]\nhost = localhost\n", encoding="utf-8")
    locked.chmod(0)
    try:
        with pytest.raises(
            InputError,
            match=f"unable to read '{re.escape(str(locked))}': permission denied",
        ):
            compare_files(locked, other)
    finally:
        locked.chmod(0o644)


def test_invalid_utf8(tmp_path: Path) -> None:
    """Invalid UTF-8 is an input error, not a replacement character."""
    bad = tmp_path / "notes.ini"
    other = tmp_path / "other.ini"
    bad.write_bytes(b"\xff")
    other.write_text("[database]\nhost = localhost\n", encoding="utf-8")
    with pytest.raises(
        InputError,
        match=f"unable to read '{re.escape(str(bad))}': invalid UTF-8",
    ):
        compare_files(bad, other)


def test_identical_files_keep_the_given_path(tmp_path: Path) -> None:
    """file_a is the path string passed in, and matching files are identical."""
    path = tmp_path / "app.ini"
    path.write_text("[database]\nhost = localhost\n", encoding="utf-8")
    result = compare_files(path, path)
    assert result.identical is True
    assert result.file_a == str(path)
    assert result.file_b == str(path)
