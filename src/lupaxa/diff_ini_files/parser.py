"""Strict INI reader. No interpolation and no inherited defaults."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import NoReturn

from lupaxa.diff_ini_files.errors import ParseError
from lupaxa.diff_ini_files.model import Entry, IniDocument, Section


@dataclass
class _Build:
    name: str
    entries: dict[str, Entry] = field(default_factory=dict)
    folds: dict[str, str] = field(default_factory=dict)
    header_seen: bool = False


def parse(text: str, *, source: str, ignore_case: bool = False) -> IniDocument:
    """Parse ``text`` identified as ``source`` into an explicit document."""
    if text.startswith("\ufeff"):
        text = text[1:]
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    by_fold: dict[str, _Build] = {}
    current: _Build | None = None
    open_value: Entry | None = None

    def fold(name: str) -> str:
        return name.casefold() if ignore_case else name

    def fail(detail: str) -> NoReturn:
        raise ParseError(f"unable to parse {source!r}: {detail}")

    def default_bucket() -> _Build:
        folded = fold("DEFAULT")
        found = by_fold.get(folded)
        if found is None:
            found = _Build(name="DEFAULT", header_seen=False)
            by_fold[folded] = found
        return found

    def add_key(section: _Build, key: str, value: str, lineno: int) -> Entry:
        folded = fold(key)
        if folded in section.folds:
            fail(f"duplicate key {key!r} in section [{section.name}] at line {lineno}")
        entry = Entry(key=key, value=value)
        section.folds[folded] = key
        section.entries[key] = entry
        return entry

    def open_header(name: str, lineno: int) -> _Build:
        folded = fold(name)
        found = by_fold.get(folded)
        if found is None:
            created = _Build(name=name, header_seen=True)
            by_fold[folded] = created
            return created
        if folded == fold("DEFAULT") and not found.header_seen:
            found.header_seen = True
            found.name = name
            return found
        raise ParseError(f"unable to parse {source!r}: duplicate section [{name}] at line {lineno}")

    for index, line in enumerate(normalized.split("\n")):
        lineno = index + 1
        if open_value is not None and (line.startswith(" ") or line.startswith("\t")):
            if line.strip() == "":
                open_value = None
                continue
            body = line.lstrip(" \t")
            if body[:1] in "#;":
                continue
            open_value.value = f"{open_value.value}\n{_strip_inline(body)}"
            continue
        open_value = None
        if line.strip() == "":
            continue
        if line.lstrip(" \t")[:1] in "#;":
            continue
        is_header, header_name = _match_section(line)
        if is_header:
            if header_name == "":
                fail(f"invalid syntax at line {lineno}")
            current = open_header(header_name, lineno)
            continue
        if "=" not in line:
            fail(f"invalid syntax at line {lineno}")
        raw_key, raw_value = line.split("=", 1)
        key = raw_key.strip()
        if key == "":
            fail(f"invalid syntax at line {lineno}")
        value = _strip_inline(raw_value.lstrip(" \t"))
        section = current if current is not None else default_bucket()
        open_value = add_key(section, key, value, lineno)

    sections = {
        item.name: Section(name=item.name, entries=dict(item.entries)) for item in by_fold.values()
    }
    return IniDocument(sections=sections)


def _strip_inline(text: str) -> str:
    """Drop a trailing inline comment and the whitespace that introduces it.

    When the value opens with ``"`` or ``'`` and that same mark closes later,
    the quoted span is left intact. An unclosed quote is scanned from the start.
    """
    start = 0
    opener = text[:1]
    if opener in "\"'":
        closer = text.find(opener, 1)
        if closer >= 0:
            start = closer + 1
    for index in range(start, len(text)):
        if text[index] in "#;" and index > 0 and text[index - 1] in " \t":
            return text[:index].rstrip(" \t")
    return text


def _match_section(line: str) -> tuple[bool, str]:
    """Return whether ``line`` is a section header, and the stripped name."""
    stripped = line.lstrip(" \t")
    if not stripped.startswith("["):
        return False, ""
    end = stripped.find("]")
    if end < 0:
        return True, ""
    name = stripped[1:end].strip()
    rest = _strip_inline(stripped[end + 1 :])
    if rest.strip() != "":
        return True, ""
    return True, name
