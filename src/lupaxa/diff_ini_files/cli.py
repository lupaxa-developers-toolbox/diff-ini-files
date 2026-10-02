"""Command-line interface for comparing two INI files."""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from typing import NoReturn

from lupaxa.diff_ini_files import CompareOptions, DiffIniError, compare_files, get_version
from lupaxa.diff_ini_files.render import render

_FORMATS = frozenset({"table", "text", "unified", "json"})
_COLOR_FORMATS = frozenset({"table", "text", "unified"})


class _Parser(argparse.ArgumentParser):
    """Argument parser that prefixes errors and exits 2."""

    def error(self, message: str) -> NoReturn:
        """Write ``Error:`` plus ``message`` and exit 2."""
        self.exit(2, f"Error: {message}\n")


def main(argv: list[str] | None = None) -> int:
    """Compare two INI files and print a report."""
    parser = _parser()
    args = parser.parse_args(argv)
    fmt = str(args.format)
    if fmt not in _FORMATS:
        sys.stderr.write(f"Error: invalid format {fmt!r}\n")
        return 2
    width = _width(None if args.width is None else str(args.width))
    if width is None:
        return 2
    try:
        result = compare_files(
            args.file_a,
            args.file_b,
            CompareOptions(
                ignore_case=bool(args.ignore_case),
                ignore_whitespace=bool(args.ignore_whitespace),
            ),
        )
    except DiffIniError as exc:
        sys.stderr.write(f"Error: {exc}\n")
        return 2
    code = 0 if result.identical else 1
    if args.quiet:
        return code
    sys.stdout.write(
        render(
            result,
            fmt=fmt,
            show_common=bool(args.show_common),
            color=_color(fmt, bool(args.no_color)),
            width=width,
        )
    )
    return code


def _parser() -> _Parser:
    """Build the diff-ini-files argument parser."""
    parser = _Parser(
        prog="diff-ini-files",
        description="Compare two INI files by section, key, and value.",
    )
    parser.add_argument(
        "--show-common",
        action="store_true",
        help="Include identical keys in the report.",
    )
    parser.add_argument(
        "--ignore-case",
        action="store_true",
        help="Compare names and values without case.",
    )
    parser.add_argument(
        "--ignore-whitespace",
        action="store_true",
        help="Ignore leading and trailing whitespace in values.",
    )
    parser.add_argument(
        "--format",
        default="table",
        help="Report format: table, text, unified, or json. Default: table.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Print nothing; still exit 0 when the files match and 1 when they differ.",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable ANSI colour.",
    )
    parser.add_argument(
        "--width",
        help="Table width in columns. Default: the terminal width, or 80.",
    )
    parser.add_argument("--version", action="version", version=get_version())
    parser.add_argument("file_a", metavar="FILE_A", help="First INI file.")
    parser.add_argument("file_b", metavar="FILE_B", help="Second INI file.")
    return parser


def _width(raw: str | None) -> int | None:
    """Return a positive column count, or ``None`` after writing an error."""
    if raw is None:
        if sys.stdout.isatty():
            return shutil.get_terminal_size(fallback=(80, 24)).columns
        return 80
    try:
        width = int(raw)
    except ValueError:
        sys.stderr.write(f"Error: invalid width {raw!r}\n")
        return None
    if width < 1:
        sys.stderr.write(f"Error: invalid width {raw!r}\n")
        return None
    return width


def _color(fmt: str, no_color: bool) -> bool:
    """Return whether this report should use ANSI colour."""
    if fmt not in _COLOR_FORMATS or no_color or not sys.stdout.isatty():
        return False
    return "NO_COLOR" not in os.environ
