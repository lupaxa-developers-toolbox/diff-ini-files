"""Structural INI comparison library."""

from __future__ import annotations

from lupaxa.diff_ini_files.api import compare_files
from lupaxa.diff_ini_files.compare import DiffResult
from lupaxa.diff_ini_files.errors import DiffIniError, InputError, ParseError
from lupaxa.diff_ini_files.options import CompareOptions
from lupaxa.diff_ini_files.version import __version__, get_version

__all__ = [
    "CompareOptions",
    "DiffIniError",
    "DiffResult",
    "InputError",
    "ParseError",
    "__version__",
    "compare_files",
    "get_version",
]
