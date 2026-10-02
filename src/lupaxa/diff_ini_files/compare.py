"""Structural comparison of two explicit INI documents."""

from __future__ import annotations

from dataclasses import dataclass

from lupaxa.diff_ini_files.model import IniDocument, Section
from lupaxa.diff_ini_files.options import CompareOptions


@dataclass(frozen=True)
class SectionEntry:
    """One key stored on a one-sided section."""

    key: str
    value: str


@dataclass(frozen=True)
class SectionDiff:
    """A section that exists in only one file."""

    type: str
    section: str
    entries: tuple[SectionEntry, ...]

    def to_dict(self) -> dict[str, object]:
        """Return this row as a JSON object."""
        entries = [{"key": item.key, "value": item.value} for item in self.entries]
        return {"type": self.type, "section": self.section, "entries": entries}


@dataclass(frozen=True)
class KeyDiff:
    """A key missing on one side, or whose values differ or match."""

    type: str
    section: str
    key: str
    value_a: str | None
    value_b: str | None

    def to_dict(self) -> dict[str, object]:
        """Return this row as a JSON object."""
        return {
            "type": self.type,
            "section": self.section,
            "key": self.key,
            "value_a": self.value_a,
            "value_b": self.value_b,
        }


@dataclass(frozen=True)
class Summary:
    """Counts for every difference class, including hidden identical keys."""

    sections_only_a: int
    sections_only_b: int
    keys_only_a: int
    keys_only_b: int
    values_different: int
    values_identical: int

    def to_dict(self) -> dict[str, int]:
        """Return the summary object in documented key order."""
        return {
            "sections_only_a": self.sections_only_a,
            "sections_only_b": self.sections_only_b,
            "keys_only_a": self.keys_only_a,
            "keys_only_b": self.keys_only_b,
            "values_different": self.values_different,
            "values_identical": self.values_identical,
        }


DiffItem = SectionDiff | KeyDiff


@dataclass(frozen=True)
class DiffResult:
    """One comparison, including identical keys."""

    file_a: str
    file_b: str
    identical: bool
    summary: Summary
    differences: tuple[DiffItem, ...]

    def to_dict(self, *, include_identical: bool = False) -> dict[str, object]:
        """Return the JSON document. Identical rows are optional."""
        rows: list[dict[str, object]] = []
        for item in self.differences:
            if item.type == "value_identical" and not include_identical:
                continue
            rows.append(item.to_dict())
        return {
            "file_a": self.file_a,
            "file_b": self.file_b,
            "identical": self.identical,
            "summary": self.summary.to_dict(),
            "differences": rows,
        }


def compare_documents(
    doc_a: IniDocument,
    doc_b: IniDocument,
    options: CompareOptions | None = None,
    *,
    file_a: str = "a",
    file_b: str = "b",
) -> DiffResult:
    """Compare two documents parsed with the same ``ignore_case`` setting."""
    chosen = options if options is not None else CompareOptions()
    left = _index(doc_a, chosen.ignore_case)
    right = _index(doc_b, chosen.ignore_case)
    items: list[DiffItem] = []
    for folded in set(left) | set(right):
        sec_a = left.get(folded)
        sec_b = right.get(folded)
        if sec_a is None and sec_b is not None:
            items.append(_section_only("section_only_b", sec_b, chosen.ignore_case))
        elif sec_b is None and sec_a is not None:
            items.append(_section_only("section_only_a", sec_a, chosen.ignore_case))
        elif sec_a is not None and sec_b is not None:
            items.extend(_key_rows(sec_a.name, sec_a, sec_b, chosen))
    items.sort(key=lambda item: _item_sort(item, chosen.ignore_case))
    summary = _summary(items)
    identical = not any(
        (
            summary.sections_only_a,
            summary.sections_only_b,
            summary.keys_only_a,
            summary.keys_only_b,
            summary.values_different,
        )
    )
    return DiffResult(
        file_a=file_a,
        file_b=file_b,
        identical=identical,
        summary=summary,
        differences=tuple(items),
    )


def _index(document: IniDocument, ignore_case: bool) -> dict[str, Section]:
    return {_fold(section.name, ignore_case): section for section in document.sections.values()}


def _fold(name: str, ignore_case: bool) -> str:
    return name.casefold() if ignore_case else name


def _sort_key(name: str, ignore_case: bool) -> tuple[str, ...]:
    if ignore_case:
        return (name.casefold(), name)
    return (name,)


def _norm(value: str, options: CompareOptions) -> str:
    if options.ignore_whitespace:
        lines = [part.strip() for part in value.split("\n")]
        value = "\n".join(lines).strip()
    if options.ignore_case:
        value = value.casefold()
    return value


def _section_only(kind: str, section: Section, ignore_case: bool) -> SectionDiff:
    ordered = sorted(section.entries.values(), key=lambda item: _sort_key(item.key, ignore_case))
    entries = tuple(SectionEntry(key=entry.key, value=entry.value) for entry in ordered)
    return SectionDiff(type=kind, section=section.name, entries=entries)


def _key_rows(
    section_name: str,
    sec_a: Section,
    sec_b: Section,
    options: CompareOptions,
) -> list[KeyDiff]:
    left = {_fold(entry.key, options.ignore_case): entry for entry in sec_a.entries.values()}
    right = {_fold(entry.key, options.ignore_case): entry for entry in sec_b.entries.values()}
    rows: list[KeyDiff] = []
    for folded in set(left) | set(right):
        side_a = left.get(folded)
        side_b = right.get(folded)
        if side_a is None and side_b is not None:
            rows.append(KeyDiff("key_only_b", section_name, side_b.key, None, side_b.value))
        elif side_b is None and side_a is not None:
            rows.append(KeyDiff("key_only_a", section_name, side_a.key, side_a.value, None))
        elif side_a is not None and side_b is not None:
            same = _norm(side_a.value, options) == _norm(side_b.value, options)
            kind = "value_identical" if same else "value_different"
            rows.append(KeyDiff(kind, section_name, side_a.key, side_a.value, side_b.value))
    return rows


def _item_sort(item: DiffItem, ignore_case: bool) -> tuple[tuple[str, ...], tuple[str, ...]]:
    section_key = _sort_key(item.section, ignore_case)
    if isinstance(item, SectionDiff):
        return section_key, ("",)
    return section_key, _sort_key(item.key, ignore_case)


def _summary(items: list[DiffItem]) -> Summary:
    return Summary(
        sections_only_a=sum(item.type == "section_only_a" for item in items),
        sections_only_b=sum(item.type == "section_only_b" for item in items),
        keys_only_a=sum(item.type == "key_only_a" for item in items),
        keys_only_b=sum(item.type == "key_only_b" for item in items),
        values_different=sum(item.type == "value_different" for item in items),
        values_identical=sum(item.type == "value_identical" for item in items),
    )
