"""Allow ``python -m lupaxa.diff_ini_files`` to run the CLI."""

from __future__ import annotations

from lupaxa.diff_ini_files.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
