# Total Export Prepare CLI Examples

## Scope / Safety Note

`total_export_prepare_cli.py` is local-only. It prepares Total Export package shells and optional local review files.

It does not fetch comments, live chat, media, screenshots, archives, or network/API content. It is not wired into the GUI or existing TXT/CSV/Excel/JSON export flows.

## Basic Plain-Text Example

```cmd
python total_export_prepare_cli.py --base-folder ".\total_export_dev" --source-url "https://www.youtube.com/watch?v=aB3_dE-9xYz" --package-id "dev package" --capture-option comments --no-create-asset-folders
```

## JSON Example

```cmd
python total_export_prepare_cli.py --base-folder ".\total_export_dev" --source-url "https://www.youtube.com/watch?v=aB3_dE-9xYz&t=30s" --package-id "json dev package" --capture-option comments --capture-option archive_check --term Caltheris --term Nyxara --json
```

## List Capture Options

This mode does not require `--base-folder` or `--source-url`, and it does not create a package.

```cmd
python total_export_prepare_cli.py --list-capture-options
```

```cmd
python total_export_prepare_cli.py --list-capture-options --json
```

## List Source Adapters

This mode is metadata-only. It does not require `--base-folder` or `--source-url`, does not fetch source content, and does not create a package.

```cmd
python total_export_prepare_cli.py --list-source-adapters
```

```cmd
python total_export_prepare_cli.py --list-source-adapters --json
```

## List ASR Providers

This mode is metadata-only. It does not call ASR providers, perform transcription, or create a package.

```cmd
python total_export_prepare_cli.py --list-asr-providers
```

```cmd
python total_export_prepare_cli.py --list-asr-providers --json
```

## List All Metadata

This mode lists capture options, source adapters, and ASR providers without creating a package.

```cmd
python total_export_prepare_cli.py --list-metadata
```

```cmd
python total_export_prepare_cli.py --list-metadata --json
```

## Explain Source Plan

Explain mode requires `--source-url`, but it does not require `--base-folder` and does not create a package.

```cmd
python total_export_prepare_cli.py --explain-plan --source-url "https://www.youtube.com/watch?v=aB3_dE-9xYz" --source-label "YouTube clip" --title "Clip Title" --capture-option comments --term Caltheris
```

```cmd
python total_export_prepare_cli.py --explain-plan --source-url "https://www.youtube.com/watch?v=aB3_dE-9xYz" --capture-option comments --term Caltheris --json
```

## Review-File Example

```cmd
python total_export_prepare_cli.py --base-folder ".\total_export_dev" --source-url "https://www.youtube.com/watch?v=aB3_dE-9xYz" --package-id "review files package" --capture-option comments --write-readme --write-inventory-report --include-inventory
```

## Review-File Shortcut

`--review-files` is equivalent to enabling `--write-readme`, `--write-inventory-report`, and `--include-inventory`.

```cmd
python total_export_prepare_cli.py --base-folder ".\total_export_dev" --source-url "https://www.youtube.com/watch?v=aB3_dE-9xYz" --package-id "review files shortcut" --capture-option comments --review-files
```

## No-Registration Example

```cmd
python total_export_prepare_cli.py --base-folder ".\total_export_dev" --source-url "https://www.youtube.com/watch?v=aB3_dE-9xYz" --package-id "unregistered review files" --capture-option comments --no-register-summary --write-readme --no-register-readme --write-inventory-report --no-register-inventory-report
```

## Important Flags

- `--capture-option`: Adds a planned capture option such as `comments` or `archive_check`.
- `--term`: Adds a user glossary/context term for the source capture plan.
- `--write-readme`: Writes `README_TOTAL_EXPORT.txt`.
- `--write-inventory-report`: Writes `TOTAL_EXPORT_INVENTORY.txt`.
- `--include-inventory`: Prints local file-vs-manifest inventory data.
- `--json`: Prints deterministic JSON output instead of plain text.
- `--no-final-validation`: Skips final local manifest/package validation.
- `--no-create-asset-folders`: Avoids creating empty asset subfolders.

## Generated Files

- Manifest JSON, named from the package ID.
- `TOTAL_EXPORT_SUMMARY.txt`.
- `README_TOTAL_EXPORT.txt`, when requested.
- `TOTAL_EXPORT_INVENTORY.txt`, when requested.

## Expected Behavior

Unsupported source URLs still return process exit code `0` if the helper completes. Unsupported status is represented in the plan status and warnings.

Validation is local manifest/package validation only. Inventory is local file-vs-manifest comparison only.
