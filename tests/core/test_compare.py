"""Structural comparison tests."""

from __future__ import annotations

from typing import cast

from lupaxa.diff_ini_files.compare import DiffResult, compare_documents
from lupaxa.diff_ini_files.options import CompareOptions
from lupaxa.diff_ini_files.parser import parse


def _cmp(left: str, right: str, options: CompareOptions | None = None) -> DiffResult:
    return compare_documents(
        parse(left, source="a.ini", ignore_case=bool(options and options.ignore_case)),
        parse(right, source="b.ini", ignore_case=bool(options and options.ignore_case)),
        options,
        file_a="a.ini",
        file_b="b.ini",
    )


def test_reordered_files_are_identical() -> None:
    """Section order and key order are not differences."""
    left = "[database]\nhost = localhost\nport = 5432\n\n[logging]\nlevel = INFO\n"
    right = "[logging]\nlevel = INFO\n\n[database]\nport = 5432\nhost = localhost\n"
    result = _cmp(left, right)
    assert result.identical is True
    assert result.summary.values_identical == 3
    assert result.to_dict()["differences"] == []


def test_comments_do_not_differ() -> None:
    """Comment text is ignored."""
    left = "# Production\n[database]\nhost = localhost\n"
    right = "# Main\n[database]\nhost = localhost\n"
    assert _cmp(left, right).identical is True


def test_hash_inside_quotes_is_a_difference() -> None:
    """A hash inside a closed quote is part of the value."""
    left = '[database]\nmsg = "alpha # one"\n'
    right = '[database]\nmsg = "alpha # two"\n'
    assert _cmp(left, right).identical is False


def test_section_only_each_side_includes_an_empty_section() -> None:
    """A section with no keys is still a section difference."""
    left = "[cache]\n\n[database]\nhost = localhost\n"
    right = "[database]\nhost = localhost\n\n[security]\n"
    result = _cmp(left, right)
    kinds = [item.type for item in result.differences if item.type != "value_identical"]
    assert kinds == ["section_only_a", "section_only_b"]
    assert result.summary.sections_only_a == 1
    assert result.summary.sections_only_b == 1
    assert result.summary.keys_only_a == 0


def test_key_only_and_different_value() -> None:
    """Missing keys and changed values are separate rows."""
    left = "[database]\nhost = localhost\nport = 5432\n"
    right = "[database]\nhost = localhost\nusername = admin\n"
    result = _cmp(left, right)
    visible = result.to_dict()["differences"]
    assert visible == [
        {
            "type": "key_only_a",
            "section": "database",
            "key": "port",
            "value_a": "5432",
            "value_b": None,
        },
        {
            "type": "key_only_b",
            "section": "database",
            "key": "username",
            "value_a": None,
            "value_b": "admin",
        },
    ]
    assert result.summary.values_identical == 1
    assert result.identical is False


def test_empty_value_is_not_missing() -> None:
    """An empty string stays distinct from a missing key."""
    result = _cmp("[database]\nusername =\n", "[database]\nusername = admin\n")
    differences = cast(list[dict[str, object]], result.to_dict()["differences"])
    row = differences[0]
    assert row["value_a"] == ""
    assert row["value_b"] == "admin"
    assert row["type"] == "value_different"


def test_default_is_not_copied_into_other_sections() -> None:
    """A DEFAULT change is not also reported inside server."""
    left = "[DEFAULT]\ntimeout = 30\n\n[server]\nhost = localhost\n"
    right = "[DEFAULT]\ntimeout = 60\n\n[server]\nhost = localhost\n"
    visible = _cmp(left, right).to_dict()["differences"]
    assert visible == [
        {
            "type": "value_different",
            "section": "DEFAULT",
            "key": "timeout",
            "value_a": "30",
            "value_b": "60",
        }
    ]


def test_ignore_whitespace_and_case_keep_stored_text() -> None:
    """Folding changes equality and not the stored spelling."""
    left = "[Database]\nlevel = INFO \n"
    right = "[database]\nlevel = info\n"
    options = CompareOptions(ignore_case=True, ignore_whitespace=True)
    result = _cmp(left, right, options)
    assert result.identical is True
    differences = cast(
        list[dict[str, object]], result.to_dict(include_identical=True)["differences"]
    )
    row = differences[0]
    assert row["section"] == "Database"
    assert row["value_a"] == "INFO "
    assert row["value_b"] == "info"


def test_spec_example_shape() -> None:
    """The production and staging example reports five visible differences."""
    production = (
        "[database]\nhost = localhost\nport = 5432\nssl = true\n\n"
        "[logging]\nlevel = INFO\n\n[cache]\nenabled = true\n"
    )
    staging = (
        "[logging]\nlevel = DEBUG\n\n[database]\nssl = true\n"
        "username = staging\nport = 3306\nhost = localhost\n\n"
        "[security]\nenabled = true\n"
    )
    result = _cmp(production, staging)
    assert result.summary.sections_only_a == 1
    assert result.summary.sections_only_b == 1
    assert result.summary.keys_only_a == 0
    assert result.summary.keys_only_b == 1
    assert result.summary.values_different == 2
    assert result.summary.values_identical == 2
    visible = cast(list[dict[str, object]], result.to_dict()["differences"])
    assert [item["type"] for item in visible] == [
        "section_only_a",
        "value_different",
        "key_only_b",
        "value_different",
        "section_only_b",
    ]
    assert visible[0]["entries"] == [{"key": "enabled", "value": "true"}]


def test_dict_key_order() -> None:
    """JSON objects use the documented key order."""
    result = _cmp("[cache]\n", "[security]\nenabled = true\n")
    document = result.to_dict()
    assert list(document) == ["file_a", "file_b", "identical", "summary", "differences"]
    assert list(cast(dict[str, object], document["summary"])) == [
        "sections_only_a",
        "sections_only_b",
        "keys_only_a",
        "keys_only_b",
        "values_different",
        "values_identical",
    ]
