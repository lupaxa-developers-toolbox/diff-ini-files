"""Version shape for lupaxa.diff_ini_files."""

from __future__ import annotations

from lupaxa.diff_ini_files import version as version_mod
from lupaxa.diff_ini_files.version import get_version


def test_version_is_semver_like() -> None:
    """The package version has numeric major and minor parts."""
    assert isinstance(version_mod.__version__, str)
    parts = version_mod.__version__.split(".")
    assert len(parts) >= 2
    assert all(part.isdigit() for part in parts[:2])


def test_get_version_matches_dunder() -> None:
    """``get_version()`` returns the module's ``__version__``."""
    assert get_version() == version_mod.__version__
