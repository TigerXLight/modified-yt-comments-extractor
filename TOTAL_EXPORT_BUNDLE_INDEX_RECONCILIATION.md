# Total Export Bundle Index Reconciliation

Date: 2026-07-10

## Purpose

`total_export_bundle_index_reconcile.py` provides a local-only comparison between an expected list of Total Export bundle ZIP paths and a `BundleIndexResult` produced by `total_export_bundle_index.py`.

It reports:

- Expected ZIPs that are present in the local bundle index.
- Expected ZIPs that are missing from the local bundle index.
- Indexed ZIPs that are not in the expected list.
- Expected ZIPs whose SHA-256 or inspection sidecars are missing, mismatched, unreadable, or otherwise need review.
- Deterministic local warnings and recommended manual follow-up actions.

## Scope

The helper accepts expected entries and an already-built in-memory bundle index result. It compares normalized local paths and does not require an expected path to exist before reconciliation.

It does not extract ZIP files or read files inside ZIPs. It does not fetch sources, download media, scrape pages, capture screenshots, check or submit archive URLs, transcribe media, call providers or APIs, store credentials, or wire into the GUI.

## Inputs

Expected entries may be supplied as simple path strings or `ExpectedBundleEntry` records with optional:

- `package_id`
- `source_url`
- `notes`

The current bundle index provides local ZIP paths, sidecar status, warnings, and recommended actions. Sidecar issues in reconciliation output come from that existing helper.

## Status Meanings

- `present`: The expected ZIP is indexed and its bundle-index status is `complete`.
- `missing_expected_zip`: The expected path did not match a ZIP in the supplied local index.
- `present_needs_review`: The expected ZIP is indexed, but its index status is not `complete`.
- `unexpected_zip`: The index contains a ZIP that was not in the expected list.

Missing expected files and unexpected local files are manual follow-up signals only. They are not proof that content was deleted, that a bundle is invalid, or that an external source is available or unavailable.

## Output

The helper provides:

- Per-item expected and matched paths.
- Bundle-index status and sidecar completeness.
- Follow-up flags, warnings, and recommended actions.
- Expected, present, missing, unexpected, and follow-up counts.
- Deterministic dictionary, plain-text, and Markdown representations.

## Local CLI Usage

`total_export_bundle_index_reconcile_cli.py` reads a local expected bundle list, builds a local bundle index from a selected root folder, reconciles the two, and renders text, Markdown, or JSON.

Example commands:

```cmd
python total_export_bundle_index_reconcile_cli.py --root path\to\bundles --expected EXPECTED_BUNDLES.json
python total_export_bundle_index_reconcile_cli.py --root path\to\bundles --expected EXPECTED_BUNDLES.txt
python total_export_bundle_index_reconcile_cli.py --root path\to\bundles --expected EXPECTED_BUNDLES.json --format markdown
python total_export_bundle_index_reconcile_cli.py --root path\to\bundles --expected EXPECTED_BUNDLES.json --format json
python total_export_bundle_index_reconcile_cli.py --root path\to\bundles --expected EXPECTED_BUNDLES.json --recursive
python total_export_bundle_index_reconcile_cli.py --root path\to\bundles --expected EXPECTED_BUNDLES.json --no-compute-hash
python total_export_bundle_index_reconcile_cli.py --root path\to\bundles --expected EXPECTED_BUNDLES.json --format markdown --output TOTAL_EXPORT_BUNDLE_INDEX_RECONCILE_REPORT.md --overwrite
```

JSON input may be an object containing an `expected_bundles` list or a bare list. Entries may be path strings or objects with `expected_zip_path` and optional `package_id`, `source_url`, and `notes`. Text input ignores blank lines and lines beginning with `#`; each remaining line is an expected ZIP path.

`--recursive` includes ZIP files in nested folders. `--no-compute-hash` skips local ZIP hash computation and leaves relevant sidecar comparisons needing review.

The CLI writes a file only when `--output` is explicitly supplied. Existing output files are preserved unless `--overwrite` is also supplied.

The CLI does not extract ZIP files, read files inside ZIPs, fetch sources, download media, scrape pages, capture screenshots, check or submit archive URLs, transcribe media, call providers or APIs, store credentials, or wire into the GUI.

## Future Integration

Further integration should remain a separately approved milestone. The helper and CLI currently perform local reporting only and do not write reports unless the CLI receives an explicit `--output` path.

Any future integration must preserve the no-extraction, no-network, no-download, no-archive-check, no-provider-call, and no-GUI boundary unless a later behavior change is explicitly approved.
