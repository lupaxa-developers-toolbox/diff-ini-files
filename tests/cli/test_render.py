"""Report rendering tests."""

from __future__ import annotations

import json
import pathlib
import re

from lupaxa.diff_ini_files.compare import DiffResult, KeyDiff, Summary, compare_documents
from lupaxa.diff_ini_files.parser import parse
from lupaxa.diff_ini_files.render import file_labels, render

PORT_TABLE = """\
INI File Comparison
File A: a.ini
File B: b.ini

┌──────────┬──────┬───────┬───────┬─────────────────┐
│ Section  │ Key  │ a.ini │ b.ini │ Status          │
├──────────┼──────┼───────┼───────┼─────────────────┤
│ database │ port │ 5432  │ 3306  │ VALUE DIFFERENT │
└──────────┴──────┴───────┴───────┴─────────────────┘
Summary

Sections only in a.ini: 0
Sections only in b.ini: 0
Keys only in a.ini:     0
Keys only in b.ini:     0
Different values:       1
Identical values:       0

Files are different.
"""

TEXT_SECTION_DIFF = """\
SECTION ONLY IN A
[cache]
enabled = true

DIFFERENCES
[database]
port
  a.ini: 5432
  b.ini: 3306
username
  a.ini: <missing>
  b.ini: admin
Summary

Sections only in a.ini: 1
Sections only in b.ini: 0
Keys only in a.ini:     0
Keys only in b.ini:     1
Different values:       1
Identical values:       0

Files are different.
"""

UNIFIED_SECTION_DIFF = """\
-[cache]
- enabled = true
[database]
- port = 5432
+ port = 3306
+ username = admin
Summary

Sections only in a.ini: 1
Sections only in b.ini: 0
Keys only in a.ini:     0
Keys only in b.ini:     1
Different values:       1
Identical values:       0

Files are different.
"""


def _cmp(left: str, right: str, file_a: str = "a.ini", file_b: str = "b.ini") -> DiffResult:
    return compare_documents(
        parse(left, source=file_a),
        parse(right, source=file_b),
        file_a=file_a,
        file_b=file_b,
    )


def _render(
    result: DiffResult,
    fmt: str,
    *,
    show_common: bool = False,
    color: bool = False,
    width: int = 80,
) -> str:
    return render(result, fmt=fmt, show_common=show_common, color=color, width=width)


def test_file_labels_use_basenames_when_they_differ() -> None:
    """Different basenames are the labels."""
    assert file_labels("a.ini", "b.ini") == ("a.ini", "b.ini")


def test_file_labels_prepend_parents_until_they_differ() -> None:
    """A shared basename keeps parent directories until the labels differ."""
    assert file_labels("left/app.ini", "right/app.ini") == ("left/app.ini", "right/app.ini")


def test_file_labels_keep_equal_paths() -> None:
    """Equal full strings stay unchanged."""
    assert file_labels("same.ini", "same.ini") == ("same.ini", "same.ini")


def test_table_port_example_is_the_natural_grid() -> None:
    """A single value change is the 53-character grid plus the summary."""
    result = _cmp("[database]\nport = 5432\n", "[database]\nport = 3306\n")
    rendered = _render(result, "table")
    assert rendered == PORT_TABLE
    grid = [line for line in rendered.splitlines() if line.startswith(("┌", "│", "├", "└"))]
    assert grid
    assert {len(line) for line in grid} == {53}
    assert "VALUE DIFFERENT" in rendered
    assert "a.ini" in rendered
    assert "b.ini" in rendered


def test_table_preserves_trailing_whitespace_in_values() -> None:
    """Stored trailing spaces stay visible in wrapped table cells."""
    result = _cmp("[database]\nhost = localhost\n", "[database]\nhost = localhost \n")
    rendered = _render(result, "table")
    row = next(line for line in rendered.splitlines() if "localhost" in line)
    assert "│ localhost │ localhost  │" in row


def test_table_preserves_whitespace_only_value() -> None:
    """A whitespace-only stored value is not blank in the table."""
    diff = KeyDiff("value_different", "database", "flag", "  ", "x")
    result = DiffResult(
        file_a="a.ini",
        file_b="b.ini",
        identical=False,
        summary=Summary(0, 0, 0, 0, 1, 0),
        differences=(diff,),
    )
    rendered = _render(result, "table")
    row = next(line for line in rendered.splitlines() if "flag" in line)
    assert row == "│ database │ flag │       │ x     │ VALUE DIFFERENT │"


def test_table_color_paints_value_different_without_changing_width() -> None:
    """Yellow marks VALUE DIFFERENT, and ANSI bytes do not change the grid."""
    result = _cmp("[database]\nport = 5432\n", "[database]\nport = 3306\n")
    colored = _render(result, "table", color=True)
    plain = _render(result, "table", color=False)
    assert "\033[33m" in colored
    assert "VALUE DIFFERENT" in colored
    assert "\033" not in plain
    visible = re.sub(r"\033\[[0-9;]*m", "", colored)
    assert visible == plain


def test_table_colors_only_in_statuses() -> None:
    """Only-in-A statuses are red and only-in-B statuses are green."""
    result = _cmp(
        "[cache]\nenabled = true\n\n[database]\nport = 5432\n",
        "[database]\nport = 3306\nusername = admin\n",
    )
    colored = _render(result, "table", color=True)
    assert "\033[31m" in colored
    assert "SECTION ONLY IN A" in colored
    assert "\033[32m" in colored
    assert "ONLY IN B" in colored
    assert re.sub(r"\033\[[0-9;]*m", "", colored) == _render(result, "table")


def test_text_section_only_and_differences_omit_common() -> None:
    """Text prints one-sided INI and labelled differences, without COMMON."""
    result = _cmp(
        "[cache]\nenabled = true\n\n[database]\nport = 5432\n",
        "[database]\nport = 3306\nusername = admin\n",
    )
    text = _render(result, "text")
    assert text == TEXT_SECTION_DIFF
    assert "INI File Comparison" not in text
    assert "File A:" not in text
    assert "COMMON" not in text


def test_text_common_group_hides_identical_status_word() -> None:
    """COMMON holds identical keys, and the word IDENTICAL is table-only."""
    result = _cmp(
        "[cache]\nenabled = true\n\n[database]\nhost = localhost\nport = 5432\n",
        "[database]\nhost = localhost\nport = 3306\nusername = admin\n",
    )
    hidden = _render(result, "text", show_common=False)
    assert "COMMON" not in hidden
    identical = next(line for line in hidden.splitlines() if line.startswith("Identical values"))
    assert identical.rstrip().endswith("1")

    shown = _render(result, "text", show_common=True)
    head, common = shown.split("COMMON", 1)
    assert "host" not in head
    assert "localhost" in common
    assert "IDENTICAL" not in shown
    assert "port" in head


def test_text_empty_value_is_not_missing() -> None:
    """A stored empty string is ``<empty>`` and a missing key is ``<missing>``."""
    result = _cmp("[database]\nusername =\n", "[database]\n")
    text = _render(result, "text")
    assert "<empty>" in text
    assert "<missing>" in text


def test_text_section_only_empty_value_uses_bare_equals() -> None:
    """One-sided INI prints ``key =`` with nothing after the equals."""
    result = _cmp("[cache]\nflag =\n", "[database]\nhost = localhost\n")
    text = _render(result, "text")
    assert "flag =" in text.splitlines()
    assert "flag = <empty>" not in text
    unified = _render(result, "unified")
    assert "- flag =" in unified.splitlines()


def test_unified_marks_one_sided_sections_and_changed_keys() -> None:
    """Unified output uses signs for one-sided sections and changed keys."""
    result = _cmp(
        "[cache]\nenabled = true\n\n[database]\nport = 5432\n",
        "[database]\nport = 3306\nusername = admin\n",
    )
    unified = _render(result, "unified")
    assert unified == UNIFIED_SECTION_DIFF
    assert "INI File Comparison" not in unified
    assert "File A:" not in unified


def test_json_uses_null_for_missing_values_and_never_color() -> None:
    """JSON is ``to_dict`` and does not turn a missing value into an empty string."""
    result = _cmp(
        "[cache]\nenabled = true\n\n[database]\nport = 5432\n",
        "[database]\nport = 3306\nusername = admin\n",
    )
    rendered = _render(result, "json", color=True)
    assert "\033" not in rendered
    assert rendered.endswith("\n")
    assert not rendered.endswith("\n\n")
    document = json.loads(rendered)
    username = next(row for row in document["differences"] if row.get("key") == "username")
    assert username["value_a"] is None
    assert '"value_a": ""' not in rendered


def test_json_includes_identical_rows_only_when_requested() -> None:
    """``show_common`` selects ``include_identical`` for JSON."""
    result = _cmp(
        "[database]\nhost = localhost\nport = 1\n",
        "[database]\nhost = localhost\nport = 2\n",
    )
    hidden = json.loads(_render(result, "json", show_common=False))
    shown = json.loads(_render(result, "json", show_common=True))
    assert all(row["type"] != "value_identical" for row in hidden["differences"])
    matched = [row for row in shown["differences"] if row["key"] == "host"]
    assert matched[0]["type"] == "value_identical"


def test_narrow_width_still_returns_a_grid() -> None:
    """A width below the natural grid still returns box characters."""
    value = "x" * 50
    result = _cmp(f"[database]\nnote = {value}\n", "[database]\nnote = y\n")
    rendered = _render(result, "table", width=30)
    assert "│" in rendered

    tiny = _render(result, "table", width=10)
    grid = [line for line in tiny.splitlines() if set(line) & set("┌│├└")]
    assert grid
    assert all(len(line) == 21 for line in grid)


def test_identical_files_have_conclusion_and_no_grid() -> None:
    """Matching files print the identical conclusion and skip the grid."""
    result = _cmp("[database]\nhost = localhost\n", "[database]\nhost = localhost\n")
    rendered = _render(result, "table")
    assert "Files are identical." in rendered
    assert "┌" not in rendered
    assert "│" not in rendered
    assert rendered.rstrip("\n").endswith("Files are identical.")


def test_empty_section_only_in_a_uses_none_key() -> None:
    """An empty one-sided section uses ``<none>`` and ``<missing>`` in both values."""
    result = _cmp("[cache]\n", "[database]\nhost = localhost\n")
    rendered = _render(result, "table")
    row = next(line for line in rendered.splitlines() if "<none>" in line)
    assert "cache" in row
    assert row.count("<missing>") == 2
    assert "SECTION ONLY IN A" in row


def test_multiline_text_indents_and_unified_context_line() -> None:
    """Text indents a continued value, and unified context lines start with two spaces."""
    left = "[database]\nnote = hello\n world\nhost = localhost\n"
    right = "[database]\nnote = hello\n there\nhost = localhost\n"
    result = _cmp(left, right)
    text = _render(result, "text")
    assert "  a.ini: hello\n         world" in text
    unified = _render(result, "unified", show_common=True)
    assert "\n  host = localhost\n" in unified


def test_summary_numbers_share_a_column() -> None:
    """Summary counts stay in one numeric column when a count needs two digits."""
    left = "[database]\n" + "".join(f"k{index} = a\n" for index in range(10))
    right = "[database]\n" + "".join(f"k{index} = b\n" for index in range(10))
    rendered = _render(_cmp(left, right), "text")
    lines = rendered.splitlines()
    zero_line = next(line for line in lines if line.startswith("Sections only in a.ini"))
    diff_line = next(line for line in lines if line.startswith("Different values"))
    assert diff_line.rstrip().endswith("10")
    assert len(zero_line.rstrip()) == len(diff_line.rstrip())


def test_text_color_paints_differences_header() -> None:
    """Yellow marks the DIFFERENCES header when colour is enabled."""
    result = _cmp(
        "[cache]\nenabled = true\n\n[database]\nport = 5432\n",
        "[database]\nport = 3306\nusername = admin\n",
    )
    colored = _render(result, "text", color=True)
    plain = _render(result, "text", color=False)
    assert "\033[33mDIFFERENCES\033[0m" in colored
    assert "\033" not in plain


def test_unified_color_paints_minus_and_plus_lines() -> None:
    """Unified minus lines are red and plus lines are green when colour is enabled."""
    result = _cmp(
        "[cache]\nenabled = true\n\n[database]\nport = 5432\n",
        "[database]\nport = 3306\nusername = admin\n",
    )
    colored = _render(result, "unified", color=True)
    plain = _render(result, "unified", color=False)
    assert "\033[31m- enabled = true\033[0m" in colored
    assert "\033[32m+ port = 3306\033[0m" in colored
    assert "\033" not in plain


def test_render_module_does_not_import_internals() -> None:
    """``render`` imports ``DiffResult`` from the package, not the internal modules."""
    root = pathlib.Path(__file__).resolve().parents[2]
    source = root / "src" / "lupaxa" / "diff_ini_files" / "render.py"
    text = source.read_text(encoding="utf-8")
    for name in ("parser", "compare", "model", "errors"):
        assert f"diff_ini_files.{name}" not in text
        assert f"import {name}" not in text
