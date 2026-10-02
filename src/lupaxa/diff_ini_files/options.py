"""Comparison switches that do not change stored text."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CompareOptions:
    """Flags for name and value comparison."""

    ignore_case: bool = False
    ignore_whitespace: bool = False
