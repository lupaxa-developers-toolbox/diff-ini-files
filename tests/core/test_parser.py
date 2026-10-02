"""Tests for the strict INI reader."""

from __future__ import annotations

import pytest

from lupaxa.diff_ini_files import ParseError
from lupaxa.diff_ini_files.parser import parse


def test_empty_and_comments_are_an_empty_document() -> None:
    """Comments and blank lines do not create sections."""
    document = parse("# note\n\n; also\n", source="a.ini")
    assert document.sections == {}


def test_spacing_around_equals_and_kept_trailing_space() -> None:
    """Delimiter padding is removed and a trailing value space is kept."""
    padded = parse("[database]\nhost = localhost\n", source="a.ini")
    tight = parse("[database]\nhost=localhost\n", source="b.ini")
    spaced = parse("[database]\nhost = localhost \n", source="c.ini")
    assert padded.sections["database"].entries["host"].value == "localhost"
    assert tight.sections["database"].entries["host"].value == "localhost"
    assert spaced.sections["database"].entries["host"].value == "localhost "


def test_inline_comment_requires_whitespace() -> None:
    """A hash is data unless a space or tab sits immediately before it."""
    document = parse(
        "[theme]\ncolor = #fff\nhost = localhost  # prod\n",
        source="a.ini",
    )
    entries = document.sections["theme"].entries
    assert entries["color"].value == "#fff"
    assert entries["host"].value == "localhost"


def test_quoted_inline_marks_stay_in_the_value() -> None:
    """A closed quote hides marks inside it. A comment after the quote is removed."""
    document = parse(
        "[database]\n"
        'msg = "alpha # one"\n'
        "note = 'alpha ; two'\n"
        'after = "alpha" # note\n'
        'open = "alpha # one\n',
        source="a.ini",
    )
    entries = document.sections["database"].entries
    assert entries["msg"].value == '"alpha # one"'
    assert entries["note"].value == "'alpha ; two'"
    assert entries["after"].value == '"alpha"'
    assert entries["open"].value == '"alpha'


def test_quotes_and_interpolation_stay_literal() -> None:
    """Quotes and substitution syntax are stored unchanged."""
    document = parse(
        '[database]\nhost = "localhost"\nname = %(name)s\npath = ${path}\n',
        source="a.ini",
    )
    entries = document.sections["database"].entries
    assert entries["host"].value == '"localhost"'
    assert entries["name"].value == "%(name)s"
    assert entries["path"].value == "${path}"


def test_empty_value_is_stored() -> None:
    """A key with nothing after equals is present and empty."""
    document = parse("[database]\nusername =\n", source="a.ini")
    assert document.sections["database"].entries["username"].value == ""


def test_multiline_value_skips_indented_comments() -> None:
    """Indented lines continue the value. An indented comment does not."""
    text = (
        "[message]\n"
        "text = This is line one\n"
        "       This is line two  \n"
        "       # skipped\n"
        "       This is line three\n"
    )
    document = parse(text, source="a.ini")
    assert document.sections["message"].entries["text"].value == (
        "This is line one\nThis is line two  \nThis is line three"
    )


def test_blank_line_ends_a_multiline_value() -> None:
    """A blank line stops continuation."""
    text = "[message]\ntext = one\n       two\n\n[other]\nk = v\n"
    document = parse(text, source="a.ini")
    assert document.sections["message"].entries["text"].value == "one\ntwo"
    assert "other" in document.sections


def test_pre_section_keys_belong_to_default() -> None:
    """Keys before any header are stored on DEFAULT and nowhere else."""
    text = "timeout = 30\n\n[server]\nhost = localhost\n"
    document = parse(text, source="a.ini")
    assert document.sections["DEFAULT"].entries["timeout"].value == "30"
    assert "timeout" not in document.sections["server"].entries


def test_one_default_header_combines_with_pre_section_keys() -> None:
    """A single [DEFAULT] header reopens the pre-section bucket."""
    text = "timeout = 30\n\n[DEFAULT]\nretries = 3\n"
    document = parse(text, source="a.ini")
    entries = document.sections["DEFAULT"].entries
    assert entries["timeout"].value == "30"
    assert entries["retries"].value == "3"


def test_second_default_header_is_an_error() -> None:
    """Two explicit DEFAULT headers are a duplicate section."""
    text = "[DEFAULT]\na = 1\n\n[DEFAULT]\nb = 2\n"
    with pytest.raises(ParseError, match=r"duplicate section \[DEFAULT\] at line 4"):
        parse(text, source="a.ini")


def test_lowercase_default_is_a_different_section() -> None:
    """Without ignore_case, [default] is not [DEFAULT]."""
    text = "[DEFAULT]\na = 1\n\n[default]\nb = 2\n"
    document = parse(text, source="a.ini")
    assert set(document.sections) == {"DEFAULT", "default"}


def test_ignore_case_uses_the_explicit_default_spelling() -> None:
    """Case-folded DEFAULT keeps the explicit header's spelling."""
    text = "timeout = 30\n\n[Default]\nretries = 3\n"
    document = parse(text, source="a.ini", ignore_case=True)
    assert set(document.sections) == {"Default"}
    assert document.sections["Default"].entries["timeout"].value == "30"


def test_duplicate_section_reports_the_second_line() -> None:
    """The second section header is invalid."""
    text = "[database]\nhost = a\n\n[database]\nhost = b\n"
    with pytest.raises(ParseError, match=r"duplicate section \[database\] at line 4"):
        parse(text, source="app.ini")


def test_duplicate_key_reports_the_second_line() -> None:
    """The second key assignment is invalid."""
    text = "[database]\nhost = a\nhost = b\n"
    with pytest.raises(
        ParseError,
        match=r"duplicate key 'host' in section \[database\] at line 3",
    ):
        parse(text, source="app.ini")


def test_ignore_case_duplicate_section() -> None:
    """Names that differ only by case are duplicates when folding is on."""
    text = "[Database]\nhost = a\n\n[database]\nhost = b\n"
    with pytest.raises(ParseError, match=r"duplicate section \[database\] at line 4"):
        parse(text, source="app.ini", ignore_case=True)


def test_invalid_lines() -> None:
    """Missing equals, empty names, and trailing header junk are syntax errors."""
    samples = [
        "[database]\nenabled\n",
        "[]\n",
        "[database] trailing\n",
        "[database]\n= value\n",
        "[unclosed\n",
    ]
    for sample in samples:
        with pytest.raises(ParseError, match=r"invalid syntax at line"):
            parse(sample, source="bad.ini")


def test_crlf_and_bom() -> None:
    """CRLF and a leading BOM do not change the document."""
    document = parse("\ufeff[database]\r\nhost = localhost\r\n", source="a.ini")
    assert document.sections["database"].entries["host"].value == "localhost"


def test_section_name_is_stripped() -> None:
    """Spaces inside the brackets are not part of the name."""
    document = parse("[ database ]\nhost = localhost\n", source="a.ini")
    assert "database" in document.sections
