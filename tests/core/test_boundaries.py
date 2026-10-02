"""The public package stays free of CLI imports."""

from __future__ import annotations

import pathlib

import lupaxa.diff_ini_files as package

REPO_SRC = pathlib.Path(__file__).resolve().parents[2] / "src" / "lupaxa" / "diff_ini_files"
LIBRARY = (
    "__init__.py",
    "api.py",
    "compare.py",
    "errors.py",
    "model.py",
    "options.py",
    "parser.py",
    "version.py",
)


def test_public_all() -> None:
    """The package exports only the documented names."""
    assert package.__all__ == [
        "CompareOptions",
        "DiffIniError",
        "DiffResult",
        "InputError",
        "ParseError",
        "__version__",
        "compare_files",
        "get_version",
    ]


def test_library_modules_do_not_import_the_cli() -> None:
    """Library modules do not parse arguments or write reports."""
    for name in LIBRARY:
        text = (REPO_SRC / name).read_text(encoding="utf-8")
        assert "argparse" not in text
        assert "sys.stdout" not in text
        assert "cli" not in text
