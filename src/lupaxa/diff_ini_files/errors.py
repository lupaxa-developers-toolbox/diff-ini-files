"""Errors raised by parsing and file reads."""

from __future__ import annotations


class DiffIniError(Exception):
    """Base error. The text has no ``Error:`` prefix."""


class InputError(DiffIniError):
    """A path cannot be read."""


class ParseError(DiffIniError):
    """The INI text is invalid."""
