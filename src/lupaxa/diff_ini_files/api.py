"""Read two INI files and compare them."""

from __future__ import annotations

from pathlib import Path

from lupaxa.diff_ini_files.compare import DiffResult, compare_documents
from lupaxa.diff_ini_files.errors import InputError
from lupaxa.diff_ini_files.options import CompareOptions
from lupaxa.diff_ini_files.parser import parse


def compare_files(
    path_a: str | Path,
    path_b: str | Path,
    options: CompareOptions | None = None,
) -> DiffResult:
    """Compare the INI files at ``path_a`` and ``path_b``."""
    chosen = options if options is not None else CompareOptions()
    source_a = str(path_a)
    source_b = str(path_b)
    doc_a = parse(_read(path_a), source=source_a, ignore_case=chosen.ignore_case)
    doc_b = parse(_read(path_b), source=source_b, ignore_case=chosen.ignore_case)
    return compare_documents(doc_a, doc_b, chosen, file_a=source_a, file_b=source_b)


def _read(path: str | Path) -> str:
    text = str(path)
    file = Path(path)
    try:
        if not file.exists():
            raise InputError(f"'{text}' does not exist")
        if file.is_dir():
            raise InputError(f"'{text}' is a directory")
        return file.read_text(encoding="utf-8")
    except InputError:
        raise
    except PermissionError:
        raise InputError(f"unable to read '{text}': permission denied") from None
    except UnicodeDecodeError:
        raise InputError(f"unable to read '{text}': invalid UTF-8") from None
    except OSError as exc:
        reason = (exc.strerror or "read failed").lower()
        raise InputError(f"unable to read '{text}': {reason}") from None
