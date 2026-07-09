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

## Source-Plan Report Example

The source-plan report is local metadata explaining the intended capture plan only. It is not proof of actual captured content.

```cmd
python total_export_prepare_cli.py --base-folder ".\total_export_dev" --source-url "https://www.youtube.com/watch?v=aB3_dE-9xYz" --package-id "plan report package" --capture-option comments --write-plan-report
```

```cmd
python total_export_prepare_cli.py --base-folder ".\total_export_dev" --source-url "https://www.youtube.com/watch?v=aB3_dE-9xYz" --package-id "custom plan report package" --capture-option comments --write-plan-report --plan-report-filename "Custom Source Plan.txt"
```

```cmd
python total_export_prepare_cli.py --base-folder ".\total_export_dev" --source-url "https://www.youtube.com/watch?v=aB3_dE-9xYz" --package-id "unregistered plan report package" --capture-option comments --write-plan-report --no-register-plan-report
```

## Review-File Shortcut

`--review-files` is equivalent to enabling `--write-readme`, `--write-inventory-report`, and `--include-inventory`.

```cmd
python total_export_prepare_cli.py --base-folder ".\total_export_dev" --source-url "https://www.youtube.com/watch?v=aB3_dE-9xYz" --package-id "review files shortcut" --capture-option comments --review-files
```

## Full Review-File Shortcut

`--full-review-files` is equivalent to enabling `--write-readme`, `--write-plan-report`, `--write-inventory-report`, and `--include-inventory`.

Neither review shortcut fetches or captures content.

```cmd
python total_export_prepare_cli.py --base-folder ".\total_export_dev" --source-url "https://www.youtube.com/watch?v=aB3_dE-9xYz" --package-id "full review files shortcut" --capture-option comments --full-review-files
```

## Inspect Existing Package

Inspection is local-only and read-only. It does not fetch, capture, download, transcribe, or inspect source content. It does not create package files.

Use it after a prepare run to inspect manifest discovery, manifest validation, local inventory, and standard review files.

```cmd
python total_export_prepare_cli.py --inspect-package --package-folder ".\total_export_dev\full_review_files_shortcut"
```

```cmd
python total_export_prepare_cli.py --inspect-package --package-folder ".\total_export_dev\full_review_files_shortcut" --json
```

```cmd
python total_export_prepare_cli.py --inspect-package --package-folder ".\total_export_dev\full_review_files_shortcut" --manifest-path ".\total_export_dev\full_review_files_shortcut\full_review_files_shortcut_manifest.json" --json
```

## Zip Existing Package

ZIP mode is local-only. It packages an existing prepared package folder, runs local inspection before zipping, and does not fetch, capture, download, transcribe, or inspect source content.

This is not external archive submit/check behavior. The default ZIP path is a sibling `.zip` next to the package folder. Use `--overwrite-zip` to replace an existing ZIP, or `--zip-path` to choose a custom output path.

```cmd
python total_export_prepare_cli.py --zip-package --package-folder ".\total_export_dev\full_review_files_shortcut"
```

```cmd
python total_export_prepare_cli.py --zip-package --package-folder ".\total_export_dev\full_review_files_shortcut" --json
```

```cmd
python total_export_prepare_cli.py --zip-package --package-folder ".\total_export_dev\full_review_files_shortcut" --zip-path ".\total_export_dev\full_review_files_shortcut.zip" --overwrite-zip --json
```

## Inspect Existing ZIP

ZIP inspection is local-only and read-only. It does not extract by default, fetch, capture, download, transcribe, or inspect source content. It is not external archive submit/check behavior.

It reports ZIP SHA-256, manifest entry discovery, standard review-file entries, unsafe entries, and duplicate entries. Use `--include-zip-entries` to list entries. Use `--hash-zip-entries` with `--include-zip-entries` to hash entries.

```cmd
python total_export_prepare_cli.py --inspect-zip --zip-path ".\total_export_dev\full_review_files_shortcut.zip"
```

```cmd
python total_export_prepare_cli.py --inspect-zip --zip-path ".\total_export_dev\full_review_files_shortcut.zip" --json
```

```cmd
python total_export_prepare_cli.py --inspect-zip --zip-path ".\total_export_dev\full_review_files_shortcut.zip" --include-zip-entries --hash-zip-entries --json
```

## Write ZIP Sidecars

ZIP sidecar mode is local-only. It writes `.sha256` and `.inspection.json` files for an existing ZIP, inspects the ZIP before writing sidecars, and does not extract by default.

It does not fetch, capture, download, transcribe, or inspect source content. It is not external archive submit/check behavior. Default paths are `<zip>.sha256` and `<zip>.inspection.json`. Use `--overwrite-sidecars` to replace existing sidecars. Use `--include-zip-entries` and `--hash-zip-entries` to include entry-level hashes in the JSON sidecar.

```cmd
python total_export_prepare_cli.py --write-zip-sidecars --zip-path ".\total_export_dev\full_review_files_shortcut.zip"
```

```cmd
python total_export_prepare_cli.py --write-zip-sidecars --zip-path ".\total_export_dev\full_review_files_shortcut.zip" --overwrite-sidecars --json
```

```cmd
python total_export_prepare_cli.py --write-zip-sidecars --zip-path ".\total_export_dev\full_review_files_shortcut.zip" --include-zip-entries --hash-zip-entries --overwrite-sidecars --json
```

## Build Review Bundle

Review bundle mode is local-only. It prepares a package shell with full review files, inspects the package, creates a deterministic local ZIP, inspects the ZIP, and writes ZIP sidecars.

It does not fetch, capture, download, transcribe, scrape, or inspect source content. It does not extract ZIPs and is not external archive submit/check behavior.

Use `--overwrite-bundle-zip` and `--overwrite-sidecars` when rebuilding the same bundle. Use `--no-bundle-sidecars` to skip sidecar generation. Use `--bundle-zip-path` for a custom ZIP path.

```cmd
python total_export_prepare_cli.py --build-review-bundle --base-folder ".\total_export_dev" --source-url "https://www.youtube.com/watch?v=aB3_dE-9xYz" --package-id "review bundle shortcut" --capture-option comments
```

```cmd
python total_export_prepare_cli.py --build-review-bundle --base-folder ".\total_export_dev" --source-url "https://www.youtube.com/watch?v=aB3_dE-9xYz" --package-id "review bundle json" --capture-option comments --json
```

```cmd
python total_export_prepare_cli.py --build-review-bundle --base-folder ".\total_export_dev" --source-url "https://www.youtube.com/watch?v=aB3_dE-9xYz" --package-id "review bundle overwrite" --capture-option comments --overwrite-bundle-zip --overwrite-sidecars --json
```

## Plan Batch Review Bundles

Batch plan mode is a local-only dry-run. It reads a local UTF-8 source file, derives package/ZIP/sidecar paths, and detects duplicate or existing outputs.

It does not create files, fetch, capture, download, transcribe, scrape, or inspect source content. It does not extract ZIPs and is not external archive behavior.

```cmd
python total_export_prepare_cli.py --plan-batch-review-bundles --batch-source-file ".\total_export_dev\sources.txt" --batch-output-folder ".\total_export_dev\batch_output" --capture-option comments
```

```cmd
python total_export_prepare_cli.py --plan-batch-review-bundles --batch-source-file ".\total_export_dev\sources.txt" --batch-output-folder ".\total_export_dev\batch_output" --capture-option comments --json
```

## Build Batch Review Bundles

Batch review-bundle mode is local-only. It reads a local UTF-8 text file of source URLs, builds local review bundles, and optionally verifies the output folder.

It does not fetch, capture, download, transcribe, scrape, or inspect source content. It does not extract ZIPs and is not external archive behavior.

```cmd
python total_export_prepare_cli.py --build-batch-review-bundles --batch-source-file ".\total_export_dev\sources.txt" --batch-output-folder ".\total_export_dev\batch_output" --capture-option comments
```

```cmd
python total_export_prepare_cli.py --build-batch-review-bundles --batch-source-file ".\total_export_dev\sources.txt" --batch-output-folder ".\total_export_dev\batch_output" --capture-option comments --overwrite-bundle-zip --overwrite-sidecars --json
```

```cmd
python total_export_prepare_cli.py --build-batch-review-bundles --batch-source-file ".\total_export_dev\sources.txt" --batch-output-folder ".\total_export_dev\batch_output" --capture-option comments --write-batch-folder-report --overwrite-batch-folder-report --json
```

## Reconcile Batch Review Bundles

Batch reconciliation mode is local-only and read-only by default. It compares a local UTF-8 source file against expected review-bundle ZIPs and `.sha256` / `.inspection.json` sidecars.

It does not create packages by default, extract ZIPs, fetch, capture, download, transcribe, scrape, inspect source content, or contact archive services.

```cmd
python total_export_prepare_cli.py --reconcile-batch-review-bundles --batch-source-file ".\total_export_dev\sources.txt" --batch-output-folder ".\total_export_dev\batch_output" --capture-option comments
```

```cmd
python total_export_prepare_cli.py --reconcile-batch-review-bundles --batch-source-file ".\total_export_dev\sources.txt" --batch-output-folder ".\total_export_dev\batch_output" --capture-option comments --json
```

```cmd
python total_export_prepare_cli.py --reconcile-batch-review-bundles --batch-source-file ".\total_export_dev\sources.txt" --batch-output-folder ".\total_export_dev\batch_output" --write-reconcile-report --reconcile-report-path ".\total_export_dev\batch_output\TOTAL_EXPORT_BATCH_RECONCILE_REPORT.json" --overwrite-reconcile-report --json
```

## Verify Review Bundle

Verification mode is local-only and read-only. It verifies an existing ZIP against its `.sha256` and `.inspection.json` sidecars.

It does not extract ZIPs, fetch, capture, download, transcribe, scrape, or inspect source content. It is not external archive submit/check behavior.

Default sidecar paths are `<zip>.sha256` and `<zip>.inspection.json`. Use custom path flags if sidecars are stored elsewhere.

```cmd
python total_export_prepare_cli.py --verify-review-bundle --zip-path ".\total_export_dev\review_bundle_shortcut.zip"
```

```cmd
python total_export_prepare_cli.py --verify-review-bundle --zip-path ".\total_export_dev\review_bundle_shortcut.zip" --json
```

```cmd
python total_export_prepare_cli.py --verify-review-bundle --zip-path ".\total_export_dev\review_bundle_shortcut.zip" --review-bundle-sha256-path ".\total_export_dev\review_bundle_shortcut.zip.sha256" --review-bundle-inspection-json-path ".\total_export_dev\review_bundle_shortcut.zip.inspection.json" --json
```

## Verify Review Bundle Folder

Folder verification mode is local-only and read-only. It discovers `.zip` files in a folder and verifies each one against default sidecars next to the ZIP.

It does not extract ZIPs, fetch, capture, download, transcribe, scrape, or inspect source content. It is not external archive behavior.

```cmd
python total_export_prepare_cli.py --verify-review-bundle-folder --review-bundle-folder ".\total_export_dev"
```

```cmd
python total_export_prepare_cli.py --verify-review-bundle-folder --review-bundle-folder ".\total_export_dev" --recursive-review-bundles --json
```

```cmd
python total_export_prepare_cli.py --verify-review-bundle-folder --review-bundle-folder ".\total_export_dev" --write-review-bundle-folder-report --overwrite-review-bundle-folder-report --json
```

## No-Registration Example

```cmd
python total_export_prepare_cli.py --base-folder ".\total_export_dev" --source-url "https://www.youtube.com/watch?v=aB3_dE-9xYz" --package-id "unregistered review files" --capture-option comments --no-register-summary --write-readme --no-register-readme --write-inventory-report --no-register-inventory-report
```

## Important Flags

- `--capture-option`: Adds a planned capture option such as `comments` or `archive_check`.
- `--term`: Adds a user glossary/context term for the source capture plan.
- `--write-readme`: Writes `README_TOTAL_EXPORT.txt`.
- `--write-plan-report`: Writes `SOURCE_CAPTURE_PLAN.txt`.
- `--write-inventory-report`: Writes `TOTAL_EXPORT_INVENTORY.txt`.
- `--include-inventory`: Prints local file-vs-manifest inventory data.
- `--review-files`: Writes README and inventory report files, then prints inventory output.
- `--full-review-files`: Writes README, source-plan report, and inventory report files, then prints inventory output.
- `--zip-package`: Creates a deterministic local ZIP for an existing package folder after local inspection.
- `--inspect-zip`: Inspects an existing local ZIP without extracting it.
- `--write-zip-sidecars`: Writes local `.sha256` and `.inspection.json` sidecars for an existing ZIP.
- `--build-review-bundle`: Prepares full local review files, inspects the package, creates and inspects a ZIP, and optionally writes ZIP sidecars.
- `--plan-batch-review-bundles`: Dry-runs a local batch source file and reports expected package/ZIP/sidecar paths without writing files.
- `--build-batch-review-bundles`: Builds local review bundles from a local UTF-8 batch source file and can verify/report the output folder.
- `--verify-review-bundle`: Verifies an existing review bundle ZIP against local `.sha256` and `.inspection.json` sidecars without extracting it.
- `--verify-review-bundle-folder`: Verifies discovered local review bundle ZIPs in a folder against default sidecars, optionally recursively or with a local JSON report.
- `--json`: Prints deterministic JSON output instead of plain text.
- `--no-final-validation`: Skips final local manifest/package validation.
- `--no-create-asset-folders`: Avoids creating empty asset subfolders.

## Generated Files

- Manifest JSON, named from the package ID.
- `TOTAL_EXPORT_SUMMARY.txt`.
- `README_TOTAL_EXPORT.txt`, when requested.
- `SOURCE_CAPTURE_PLAN.txt`, when requested.
- `TOTAL_EXPORT_INVENTORY.txt`, when requested.

## Expected Behavior

Unsupported source URLs still return process exit code `0` if the helper completes. Unsupported status is represented in the plan status and warnings.

Validation is local manifest/package validation only. Inventory is local file-vs-manifest comparison only.
