<p align="center">
  <a href="https://github.com/lupaxa-developers-toolbox">
    <img src="https://raw.githubusercontent.com/the-lupaxa-project/brand-assets/master/logos/organisations/developers-toolbox/readme-logo.png" alt="Developers Toolbox" />
  </a>
</p>

<h1 align="center">Diff Ini Files</h1>

Compare two INI files by section, key, and value. Comments, blank lines, and the order of sections or keys are not differences. The same key with two different values is.

## Requirements

- Python 3.10+

## Install

```bash
pip install lupaxa-diff-ini-files
diff-ini-files --help
```

You can also run `python -m lupaxa.diff_ini_files`.

## Quick Start

```bash
diff-ini-files production.ini staging.ini
diff-ini-files --format json production.ini staging.ini
diff-ini-files --quiet production.ini staging.ini; echo $?
```

Exit `0` when the files match, `1` when they differ, and `2` when the comparison cannot be read. `--help` and `--version` exit `0`. `--quiet` prints nothing and still uses `0` or `1`.

Errors go to stderr as one `Error:` line. A missing file, a directory, unreadable text, and duplicate names are all exit `2`.

## What it Compares

Each file is read as the sections and keys that are actually written. `[DEFAULT]` is its own section. Its keys are not copied into the others.

- A section or key that exists on only one side is a difference, including an empty section.
- `username =` is an empty value. A key that was never written is missing. Those stay distinct.
- A line whose first non-whitespace character is `#` or `;` is a comment. An inline `#` or `;` starts a comment only when a space or tab sits immediately before it, and that space is not part of the value.
- A value that opens with `"` or `'` keeps `#` and `;` until the matching closer. `msg = "alpha # one"` stores `"alpha # one"`. `msg = "alpha" # note` stores `"alpha"`.
- `%(name)s` and `${name}` stay as written. Nothing is interpolated.
- The only delimiter is `=`. A colon is ordinary text.
- A line that starts with a space or tab continues the previous value. The lines are joined with a newline.
- A second copy of the same section or key is an error. The message names the file and the line of the second one.
- Files are UTF-8. One leading byte-order mark is discarded.

`--ignore-case` compares names and values without case. The report still shows file A's spelling when that side has the name.

`--ignore-whitespace` strips each line, then the whole value, before the compare. The text stored for display does not change, so a trailing space is still visible in the report.

## Options

| Flag                  | Effect                                                                                        |
| --------------------- | --------------------------------------------------------------------------------------------- |
| `--show-common`       | Include keys whose values match. The exit code does not change.                               |
| `--ignore-case`       | Compare section names, keys, and values without case.                                         |
| `--ignore-whitespace` | Ignore leading and trailing whitespace when comparing values. The stored text stays the same. |
| `--format FORMAT`     | `table` (default), `text`, `unified`, or `json`.                                              |
| `--quiet`             | Print nothing. Exit `0` or `1` still reports whether the files match.                         |
| `--no-color`          | Do not print ANSI colour. `NO_COLOR` does the same.                                           |
| `--width WIDTH`       | Wrap the table to this many columns. A terminal uses its width. Other output uses 80.         |
| `--version`           | Print the version and exit `0`.                                                               |
| `--help`              | Print help and exit `0`.                                                                      |

Colour is used for `table`, `text`, and `unified` when stdout is a terminal. JSON is always plain text. `--width` must be an integer of `1` or more.

| Code | Meaning                                                      |
| ---- | ------------------------------------------------------------ |
| `0`  | The files match, or the command was `--help` or `--version`. |
| `1`  | At least one section, key, or value differs.                 |
| `2`  | Bad arguments, a file that cannot be read, or invalid INI.   |

## Example

`production.ini`:

```ini
# production database
[database]
host = localhost
port = 5432
username =

[cache]
enabled = true

[logging]
level = info
```

`staging.ini`:

```ini
[database]
host = localhost
port = 3306

[logging]
level = debug

[security]
tls = required
```

`host` is the same in both files, so the default report hides it and still counts it. `username` is empty on one side and absent on the other.

```bash
diff-ini-files production.ini staging.ini
```

```text
INI File Comparison
File A: production.ini
File B: staging.ini

┌──────────┬──────────┬────────────────┬─────────────┬───────────────────┐
│ Section  │ Key      │ production.ini │ staging.ini │ Status            │
├──────────┼──────────┼────────────────┼─────────────┼───────────────────┤
│ cache    │ enabled  │ true           │ <missing>   │ SECTION ONLY IN A │
├──────────┼──────────┼────────────────┼─────────────┼───────────────────┤
│ database │ port     │ 5432           │ 3306        │ VALUE DIFFERENT   │
├──────────┼──────────┼────────────────┼─────────────┼───────────────────┤
│ database │ username │ <empty>        │ <missing>   │ ONLY IN A         │
├──────────┼──────────┼────────────────┼─────────────┼───────────────────┤
│ logging  │ level    │ info           │ debug       │ VALUE DIFFERENT   │
├──────────┼──────────┼────────────────┼─────────────┼───────────────────┤
│ security │ tls      │ <missing>      │ required    │ SECTION ONLY IN B │
└──────────┴──────────┴────────────────┴─────────────┴───────────────────┘
Summary

Sections only in production.ini: 1
Sections only in staging.ini:    1
Keys only in production.ini:     1
Keys only in staging.ini:        0
Different values:                2
Identical values:                1

Files are different.
```

When the two file names match, the column headings keep parent directories until the labels differ. JSON keeps the path strings you typed.

`--show-common` adds the matching `host` key. In the table its status is `IDENTICAL`. In text it is a separate `COMMON` group:

```text
COMMON
[database]
host
  production.ini: localhost
  staging.ini: localhost
```

### Text

```bash
diff-ini-files --format text production.ini staging.ini
```

```text
SECTION ONLY IN A
[cache]
enabled = true

SECTION ONLY IN B
[security]
tls = required

DIFFERENCES
[database]
port
  production.ini: 5432
  staging.ini: 3306
username
  production.ini: <empty>
  staging.ini: <missing>

[logging]
level
  production.ini: info
  staging.ini: debug
```

A section that exists on only one side is printed as INI. An empty value there is `key =` with nothing after the equals sign. The same summary as the table follows this body.

### Unified

```bash
diff-ini-files --format unified production.ini staging.ini
```

```text
-[cache]
- enabled = true
[database]
- port = 5432
+ port = 3306
- username =
[logging]
- level = info
+ level = debug
+[security]
+ tls = required
```

This is a structural diff in alphabetical order, not a line diff of the raw files. A shared section has a plain `[section]` header. A one-sided section marks the header itself with `-` or `+` and no space after the sign.

`--show-common` adds a context line that starts with two spaces, then `host = localhost`.

### JSON

```bash
diff-ini-files --format json production.ini staging.ini
```

```json
{
  "file_a": "production.ini",
  "file_b": "staging.ini",
  "identical": false,
  "summary": {
    "sections_only_a": 1,
    "sections_only_b": 1,
    "keys_only_a": 1,
    "keys_only_b": 0,
    "values_different": 2,
    "values_identical": 1
  },
  "differences": [
    {
      "type": "section_only_a",
      "section": "cache",
      "entries": [
        {
          "key": "enabled",
          "value": "true"
        }
      ]
    },
    {
      "type": "value_different",
      "section": "database",
      "key": "port",
      "value_a": "5432",
      "value_b": "3306"
    },
    {
      "type": "key_only_a",
      "section": "database",
      "key": "username",
      "value_a": "",
      "value_b": null
    },
    {
      "type": "value_different",
      "section": "logging",
      "key": "level",
      "value_a": "info",
      "value_b": "debug"
    },
    {
      "type": "section_only_b",
      "section": "security",
      "entries": [
        {
          "key": "tls",
          "value": "required"
        }
      ]
    }
  ]
}
```

A missing value is `null`. An empty value is `""`. `identical` is `true` only when there are no section, key, or value differences. Identical keys are omitted from `differences` unless you pass `--show-common`, and they are still counted.

## Library

```python
from lupaxa.diff_ini_files import CompareOptions, compare_files

result = compare_files(
    "production.ini",
    "staging.ini",
    CompareOptions(ignore_whitespace=True),
)
if not result.identical:
    document = result.to_dict()
```

`compare_files` returns a `DiffResult`. `to_dict()` is the JSON document above. `to_dict(include_identical=True)` adds the matching keys. `result.summary` holds the six counts even when those keys are hidden.

`InputError` is a missing path, a directory, or a file that cannot be decoded. `ParseError` is invalid INI, including a duplicate section or key. Both are `DiffIniError`. The library raises them and does not print or exit.

## Development

From a clone of this repository:

```bash
make init                # first-time makefile-skills checkout
make python-install-dev  # editable install with [dev]
make python-check        # lint, type-check, and test
```

<a href="https://github.com/the-lupaxa-project">
    <img src="https://raw.githubusercontent.com/the-lupaxa-project/brand-assets/master/logos/components/footer-for-child-orgs.svg" alt="The Lupaxa Project Footer" width="100%" />
</a>
