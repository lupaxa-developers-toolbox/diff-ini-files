"""Explicit INI documents. Missing keys are absent."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Entry:
    """One written key and the display value."""

    key: str
    value: str


@dataclass
class Section:
    """Keys written in one section, keyed by their stored spelling."""

    name: str
    entries: dict[str, Entry] = field(default_factory=dict)


@dataclass
class IniDocument:
    """Sections keyed by their stored spelling."""

    sections: dict[str, Section] = field(default_factory=dict)
