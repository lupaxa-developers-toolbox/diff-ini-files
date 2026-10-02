"""CLI modules stay on the public import boundary."""

from __future__ import annotations

import pathlib
import re

REPO_SRC = pathlib.Path(__file__).resolve().parents[2] / "src" / "lupaxa" / "diff_ini_files"
MODULES = ("cli.py", "render.py", "__main__.py")
FORBIDDEN = re.compile(
    r"from lupaxa\.diff_ini_files\.(parser|compare|model|errors) import"
    r"|import lupaxa\.diff_ini_files\.(parser|compare|model|errors)"
)


def test_cli_modules_do_not_import_internals() -> None:
    """``cli``, ``render``, and ``__main__`` do not import parser internals."""
    for name in MODULES:
        text = (REPO_SRC / name).read_text(encoding="utf-8")
        for line in text.splitlines():
            assert FORBIDDEN.search(line.strip()) is None, line
