"""Render comparison reports."""

from __future__ import annotations

import json
import textwrap
from pathlib import PurePath
from typing import cast

from lupaxa.diff_ini_files import DiffResult

_KEY_STATUS = {
    "key_only_a": "ONLY IN A",
    "key_only_b": "ONLY IN B",
    "value_different": "VALUE DIFFERENT",
    "value_identical": "IDENTICAL",
}
_STATUS_COLOR = {
    "VALUE DIFFERENT": "33",
    "ONLY IN A": "31",
    "SECTION ONLY IN A": "31",
    "ONLY IN B": "32",
    "SECTION ONLY IN B": "32",
}
_COLUMNS = 5


def file_labels(path_a: str, path_b: str) -> tuple[str, str]:
    """Return the shortest differing path tails, or the paths when equal."""
    if path_a == path_b:
        return path_a, path_b
    parts_a = PurePath(path_a).parts
    parts_b = PurePath(path_b).parts
    limit = max(len(parts_a), len(parts_b))
    for depth in range(1, limit + 1):
        label_a = _tail(parts_a, depth)
        label_b = _tail(parts_b, depth)
        if label_a != label_b:
            return label_a, label_b
    return path_a, path_b


def render(
    result: DiffResult,
    *,
    fmt: str,
    show_common: bool,
    color: bool,
    width: int,
) -> str:
    """Render ``result`` as ``table``, ``text``, ``unified``, or ``json``."""
    if fmt == "json":
        payload = result.to_dict(include_identical=show_common)
        return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    if fmt == "table":
        body = _table_body(result, show_common, color, width)
        return _human(result, body, with_title=True)
    if fmt == "text":
        body = _text_body(result, show_common)
        if color:
            body = _color_text_lines(body)
        return _human(result, body)
    if fmt == "unified":
        body = _unified_body(result, show_common)
        if color:
            body = _color_unified_lines(body)
        return _human(result, body)
    raise ValueError(f"unknown format {fmt!r}")


def _tail(parts: tuple[str, ...], depth: int) -> str:
    chosen = parts if depth >= len(parts) else parts[-depth:]
    return str(PurePath(*chosen))


def _human(result: DiffResult, body: list[str], *, with_title: bool = False) -> str:
    parts: list[str] = []
    if with_title:
        parts.extend(
            [
                "INI File Comparison",
                f"File A: {result.file_a}",
                f"File B: {result.file_b}",
                "",
            ]
        )
    parts.extend([*body, *_summary_lines(result)])
    return "\n".join(parts) + "\n"


def _summary_lines(result: DiffResult) -> list[str]:
    label_a, label_b = file_labels(result.file_a, result.file_b)
    rows = (
        (f"Sections only in {label_a}", result.summary.sections_only_a),
        (f"Sections only in {label_b}", result.summary.sections_only_b),
        (f"Keys only in {label_a}", result.summary.keys_only_a),
        (f"Keys only in {label_b}", result.summary.keys_only_b),
        ("Different values", result.summary.values_different),
        ("Identical values", result.summary.values_identical),
    )
    label_width = max(len(label) for label, _count in rows)
    number_width = max(len(str(count)) for _label, count in rows)
    count_lines = [
        f"{label}:{' ' * (label_width - len(label) + 1)}{count:>{number_width}}"
        for label, count in rows
    ]
    conclusion = "Files are identical." if result.identical else "Files are different."
    return ["Summary", "", *count_lines, "", conclusion]


def _visible(result: DiffResult, show_common: bool) -> list[dict[str, object]]:
    document = result.to_dict(include_identical=True)
    rows = cast(list[dict[str, object]], document["differences"])
    if show_common:
        return rows
    return [item for item in rows if item["type"] != "value_identical"]


def _show(value: object) -> str:
    if value is None:
        return "<missing>"
    if value == "":
        return "<empty>"
    return str(value)


def _table_body(result: DiffResult, show_common: bool, color: bool, width: int) -> list[str]:
    rows = _table_rows(result, show_common)
    if not rows:
        return []
    label_a, label_b = file_labels(result.file_a, result.file_b)
    headers = ["Section", "Key", label_a, label_b, "Status"]
    return _grid(headers, rows, width, color)


def _table_rows(result: DiffResult, show_common: bool) -> list[list[str]]:
    rows: list[list[str]] = []
    for item in _visible(result, show_common):
        kind = str(item["type"])
        section = str(item["section"])
        if kind in {"section_only_a", "section_only_b"}:
            rows.extend(_section_rows(item, kind, section))
            continue
        rows.append(
            [
                section,
                str(item["key"]),
                _show(item["value_a"]),
                _show(item["value_b"]),
                _KEY_STATUS[kind],
            ]
        )
    return rows


def _section_rows(item: dict[str, object], kind: str, section: str) -> list[list[str]]:
    status = "SECTION ONLY IN A" if kind == "section_only_a" else "SECTION ONLY IN B"
    entries = cast(list[dict[str, object]], item["entries"])
    if not entries:
        return [[section, "<none>", "<missing>", "<missing>", status]]
    rows: list[list[str]] = []
    for entry in entries:
        shown = _show(entry["value"])
        if kind == "section_only_a":
            left, right = shown, "<missing>"
        else:
            left, right = "<missing>", shown
        rows.append([section, str(entry["key"]), left, right, status])
    return rows


def _grid(headers: list[str], rows: list[list[str]], width: int, color: bool) -> list[str]:
    natural = [
        max(_measure(headers[index]), *(_measure(row[index]) for row in rows))
        for index in range(_COLUMNS)
    ]
    widths = _fit_widths(natural, width)
    lines = [_rule(widths, "┌", "┬", "┐"), *_painted_row(headers, widths, None)]
    for row in rows:
        code = _STATUS_COLOR.get(row[4]) if color else None
        lines.append(_rule(widths, "├", "┼", "┤"))
        lines.extend(_painted_row(row, widths, code))
    lines.append(_rule(widths, "└", "┴", "┘"))
    return lines


def _measure(text: str) -> int:
    return max(len(line) for line in text.split("\n"))


def _fit_widths(natural: list[int], width: int) -> list[int]:
    chrome = _COLUMNS * 2 + _COLUMNS + 1
    if sum(natural) + chrome <= width:
        return natural
    if width < _COLUMNS + chrome:
        return [1] * _COLUMNS
    budget = width - chrome
    fitted = natural[:]
    while sum(fitted) > budget:
        index = max(range(_COLUMNS), key=lambda item: (fitted[item], item))
        if fitted[index] <= 1:
            break
        fitted[index] -= 1
    return fitted


def _rule(widths: list[int], left: str, mid: str, right: str) -> str:
    parts = ["─" * (column + 2) for column in widths]
    return left + mid.join(parts) + right


def _painted_row(cells: list[str], widths: list[int], status_code: str | None) -> list[str]:
    wrapped = [_wrap_cell(cell, widths[index]) for index, cell in enumerate(cells)]
    height = max(len(lines) for lines in wrapped)
    output: list[str] = []
    for line_index in range(height):
        pieces: list[str] = []
        for index, lines in enumerate(wrapped):
            text = lines[line_index] if line_index < len(lines) else ""
            code = status_code if index == _COLUMNS - 1 else None
            pieces.append(_paint(text, widths[index], code))
        output.append("│" + "│".join(pieces) + "│")
    return output


def _wrap_cell(text: str, column_width: int) -> list[str]:
    lines: list[str] = []
    for part in text.split("\n"):
        wrapped = textwrap.wrap(
            part,
            column_width,
            expand_tabs=False,
            replace_whitespace=False,
            drop_whitespace=False,
        )
        lines.extend(wrapped if wrapped else [""])
    return lines


def _color_line(line: str, code: str) -> str:
    return f"\033[{code}m{line}\033[0m"


def _color_text_lines(lines: list[str]) -> list[str]:
    header_colors = {
        "SECTION ONLY IN A": "31",
        "SECTION ONLY IN B": "32",
        "DIFFERENCES": "33",
    }
    return [
        _color_line(line, header_colors[line]) if line in header_colors else line for line in lines
    ]


def _color_unified_lines(lines: list[str]) -> list[str]:
    colored: list[str] = []
    for line in lines:
        if line.startswith("-"):
            colored.append(_color_line(line, "31"))
        elif line.startswith("+"):
            colored.append(_color_line(line, "32"))
        else:
            colored.append(line)
    return colored


def _paint(text: str, width: int, code: str | None) -> str:
    padded = text.ljust(width)
    if code:
        padded = f"\033[{code}m{padded}\033[0m"
    return f" {padded} "


def _text_body(result: DiffResult, show_common: bool) -> list[str]:
    items = _visible(result, show_common)
    label_a, label_b = file_labels(result.file_a, result.file_b)
    groups = (
        ("SECTION ONLY IN A", _ini_block(_of_type(items, "section_only_a"))),
        ("SECTION ONLY IN B", _ini_block(_of_type(items, "section_only_b"))),
        ("DIFFERENCES", _labelled_block(_key_diffs(items), label_a, label_b)),
        ("COMMON", _labelled_block(_of_type(items, "value_identical"), label_a, label_b)),
    )
    lines: list[str] = []
    for title, block in groups:
        if not block:
            continue
        if lines:
            lines.append("")
        lines.append(title)
        lines.extend(block)
    return lines


def _of_type(items: list[dict[str, object]], kind: str) -> list[dict[str, object]]:
    return [item for item in items if item["type"] == kind]


def _key_diffs(items: list[dict[str, object]]) -> list[dict[str, object]]:
    kinds = {"key_only_a", "key_only_b", "value_different"}
    return [item for item in items if item["type"] in kinds]


def _ini_block(items: list[dict[str, object]]) -> list[str]:
    lines: list[str] = []
    for index, item in enumerate(items):
        if index:
            lines.append("")
        lines.append(f"[{item['section']}]")
        entries = cast(list[dict[str, object]], item["entries"])
        for entry in entries:
            lines.extend(_ini_lines(str(entry["key"]), str(entry["value"])))
    return lines


def _ini_lines(key: str, value: str) -> list[str]:
    if value == "":
        return [f"{key} ="]
    parts = value.split("\n")
    prefix = f"{key} = "
    indent = " " * len(prefix)
    return [prefix + parts[0], *[indent + part for part in parts[1:]]]


def _labelled_block(
    items: list[dict[str, object]],
    label_a: str,
    label_b: str,
) -> list[str]:
    lines: list[str] = []
    current: str | None = None
    for item in items:
        section = str(item["section"])
        if section != current:
            if current is not None:
                lines.append("")
            lines.append(f"[{section}]")
            current = section
        lines.append(str(item["key"]))
        lines.extend(_labelled_lines(label_a, item["value_a"]))
        lines.extend(_labelled_lines(label_b, item["value_b"]))
    return lines


def _labelled_lines(label: str, value: object) -> list[str]:
    parts = _show(value).split("\n")
    prefix = f"  {label}: "
    indent = " " * len(prefix)
    return [prefix + parts[0], *[indent + part for part in parts[1:]]]


def _unified_body(result: DiffResult, show_common: bool) -> list[str]:
    lines: list[str] = []
    open_section: str | None = None
    for item in _visible(result, show_common):
        kind = str(item["type"])
        if kind in {"section_only_a", "section_only_b"}:
            open_section = None
            sign = "-" if kind == "section_only_a" else "+"
            lines.append(f"{sign}[{item['section']}]")
            entries = cast(list[dict[str, object]], item["entries"])
            for entry in entries:
                lines.extend(_assignment(f"{sign} ", str(entry["key"]), entry["value"]))
            continue
        section = str(item["section"])
        if open_section != section:
            lines.append(f"[{section}]")
            open_section = section
        lines.extend(_unified_key(kind, item))
    return lines


def _unified_key(kind: str, item: dict[str, object]) -> list[str]:
    key = str(item["key"])
    if kind == "key_only_a":
        return _assignment("- ", key, item["value_a"])
    if kind == "key_only_b":
        return _assignment("+ ", key, item["value_b"])
    if kind == "value_different":
        return [
            *_assignment("- ", key, item["value_a"]),
            *_assignment("+ ", key, item["value_b"]),
        ]
    return _assignment("  ", key, item["value_a"])


def _assignment(prefix: str, key: str, value: object) -> list[str]:
    text = "" if value is None else str(value)
    if text == "":
        return [f"{prefix}{key} ="]
    parts = text.split("\n")
    head = f"{prefix}{key} = {parts[0]}"
    indent = " " * len(f"{prefix}{key} = ")
    return [head, *[indent + part for part in parts[1:]]]
