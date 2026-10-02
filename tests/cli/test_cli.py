"""Command-line exit codes, reports, and colour."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

from lupaxa.diff_ini_files.cli import main

_DIFFERENT_A = "[database]\nhost = localhost\nport = 5432\n"
_DIFFERENT_B = "[database]\nhost = localhost\nport = 3306\n"
_IDENTICAL = "[database]\nhost = localhost\n"


def _code(argv: list[str]) -> int:
    try:
        return main(argv)
    except SystemExit as exc:
        status = exc.code
        if status is None:
            return 0
        if isinstance(status, int):
            return status
        raise


def _pair(tmp_path: Path, left: str, right: str) -> tuple[Path, Path]:
    path_a = tmp_path / "a.ini"
    path_b = tmp_path / "b.ini"
    path_a.write_text(left, encoding="utf-8")
    path_b.write_text(right, encoding="utf-8")
    return path_a, path_b


def _argv(path_a: Path, path_b: Path, *extra: str) -> list[str]:
    return [str(path_a), str(path_b), *extra]


def test_identical_files_exit_zero(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Matching files exit 0 and say they are identical."""
    path_a, path_b = _pair(tmp_path, _IDENTICAL, _IDENTICAL)
    assert main(_argv(path_a, path_b)) == 0
    assert "Files are identical." in capsys.readouterr().out


def test_different_files_exit_one(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """A value change exits 1 and names the difference."""
    path_a, path_b = _pair(tmp_path, _DIFFERENT_A, _DIFFERENT_B)
    assert main(_argv(path_a, path_b)) == 1
    stdout = capsys.readouterr().out
    assert "VALUE DIFFERENT" in stdout or "Files are different." in stdout


def test_quiet_difference_prints_nothing(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Quiet mode keeps the difference status and skips the report."""
    path_a, path_b = _pair(tmp_path, _DIFFERENT_A, _DIFFERENT_B)
    assert main(_argv(path_a, path_b, "--quiet")) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""


def test_json_format_is_plain_json(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """JSON output parses and contains no ANSI colour."""
    path_a, path_b = _pair(tmp_path, _DIFFERENT_A, _DIFFERENT_B)
    assert main(_argv(path_a, path_b, "--format", "json")) == 1
    stdout = capsys.readouterr().out
    json.loads(stdout)
    assert "\033" not in stdout


def test_text_format_reports_differences(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Text format exits 1 and prints the DIFFERENCES heading."""
    path_a, path_b = _pair(tmp_path, _DIFFERENT_A, _DIFFERENT_B)
    assert main(_argv(path_a, path_b, "--format", "text")) == 1
    assert "DIFFERENCES" in capsys.readouterr().out


def test_unified_format_marks_removed_lines(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Unified format exits 1 and includes a removed line."""
    path_a, path_b = _pair(tmp_path, _DIFFERENT_A, _DIFFERENT_B)
    assert main(_argv(path_a, path_b, "--format", "unified")) == 1
    stdout = capsys.readouterr().out
    assert any(line.startswith("- ") for line in stdout.splitlines())


def test_yaml_format_is_rejected(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """An unknown format returns 2 with the exact error line."""
    path_a, path_b = _pair(tmp_path, _IDENTICAL, _IDENTICAL)
    assert main(_argv(path_a, path_b, "--format", "yaml")) == 2
    assert capsys.readouterr().err == "Error: invalid format 'yaml'\n"


@pytest.mark.parametrize("width", ["0", "-1", "abc"])
def test_invalid_width(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    width: str,
) -> None:
    """Zero, negative, and non-numeric widths return 2."""
    path_a, path_b = _pair(tmp_path, _DIFFERENT_A, _DIFFERENT_B)
    assert main(_argv(path_a, path_b, "--width", width)) == 2
    assert capsys.readouterr().err.startswith("Error: invalid width")


def test_narrow_width_still_draws_a_box(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """A positive width wraps the table and still draws the grid."""
    path_a, path_b = _pair(tmp_path, _DIFFERENT_A, _DIFFERENT_B)
    assert main(_argv(path_a, path_b, "--width", "40")) == 1
    assert "┌" in capsys.readouterr().out


def test_duplicate_section_exits_two(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """A duplicate section is a parse error without a traceback."""
    path_a = tmp_path / "a.ini"
    path_b = tmp_path / "b.ini"
    path_a.write_text("[database]\nhost = localhost\n\n[database]\nport = 1\n", encoding="utf-8")
    path_b.write_text(_IDENTICAL, encoding="utf-8")
    assert main(_argv(path_a, path_b)) == 2
    stderr = capsys.readouterr().err
    assert "Error: unable to parse" in stderr
    assert "duplicate section" in stderr
    assert "Traceback" not in stderr


def test_missing_file_exits_two(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """A missing path exits 2 and says it does not exist."""
    present = tmp_path / "present.ini"
    present.write_text(_IDENTICAL, encoding="utf-8")
    missing = tmp_path / "missing.ini"
    assert main(_argv(missing, present)) == 2
    assert "does not exist" in capsys.readouterr().err


def test_directory_exits_two(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """A directory path exits 2 and says it is a directory."""
    present = tmp_path / "present.ini"
    present.write_text(_IDENTICAL, encoding="utf-8")
    assert main(_argv(tmp_path, present)) == 2
    assert "is a directory" in capsys.readouterr().err


def test_help_exits_zero(capsys: pytest.CaptureFixture[str]) -> None:
    """Help exits 0, including argparse's SystemExit."""
    assert _code(["--help"]) == 0
    assert capsys.readouterr().out


def test_version_exits_zero(capsys: pytest.CaptureFixture[str]) -> None:
    """Version exits 0 and prints a semantic version."""
    assert _code(["--version"]) == 0
    assert re.search(r"\d+\.\d+", capsys.readouterr().out)


def test_no_color_on_a_tty(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``--no-color`` strips ANSI even when stdout is a terminal."""
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)
    path_a, path_b = _pair(tmp_path, _DIFFERENT_A, _DIFFERENT_B)
    assert main(_argv(path_a, path_b, "--no-color")) == 1
    assert "\033" not in capsys.readouterr().out


def test_no_color_env_on_a_tty(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``NO_COLOR`` strips ANSI on a terminal when the flag is absent."""
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)
    monkeypatch.setenv("NO_COLOR", "1")
    path_a, path_b = _pair(tmp_path, _DIFFERENT_A, _DIFFERENT_B)
    assert main(_argv(path_a, path_b)) == 1
    assert "\033" not in capsys.readouterr().out


def test_tty_colors_value_different(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A terminal table paints VALUE DIFFERENT in yellow."""
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)
    monkeypatch.delenv("NO_COLOR", raising=False)
    path_a, path_b = _pair(tmp_path, _DIFFERENT_A, _DIFFERENT_B)
    assert main(_argv(path_a, path_b)) == 1
    assert "\033[33m" in capsys.readouterr().out


def test_show_common_prints_identical(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Show-common includes IDENTICAL for a shared key."""
    path_a, path_b = _pair(tmp_path, _DIFFERENT_A, _DIFFERENT_B)
    assert main(_argv(path_a, path_b, "--show-common")) == 1
    assert "IDENTICAL" in capsys.readouterr().out


def test_ignore_case_treats_info_as_equal(tmp_path: Path) -> None:
    """``INFO`` and ``info`` match when case is ignored."""
    path_a, path_b = _pair(
        tmp_path,
        "[database]\nlevel = INFO\n",
        "[database]\nlevel = info\n",
    )
    assert main(_argv(path_a, path_b, "--ignore-case")) == 0


def test_ignore_whitespace_treats_trailing_space_as_equal(tmp_path: Path) -> None:
    """Trailing whitespace matches when whitespace is ignored."""
    path_a, path_b = _pair(
        tmp_path,
        "[database]\nhost = localhost \n",
        "[database]\nhost = localhost\n",
    )
    assert main(_argv(path_a, path_b, "--ignore-whitespace")) == 0


def test_no_file_arguments(capsys: pytest.CaptureFixture[str]) -> None:
    """Missing file arguments exit 2 and start stderr with Error:."""
    assert _code([]) == 2
    assert capsys.readouterr().err.startswith("Error:")
