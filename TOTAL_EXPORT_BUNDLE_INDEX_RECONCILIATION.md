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

## Future Integration

A reconciliation CLI may be considered only in a separately approved milestone. This helper currently performs in-memory/local reporting only and does not write reports automatically.

Any future integration must preserve the no-extraction, no-network, no-download, no-archive-check, no-provider-call, and no-GUI boundary unless a later behavior change is explicitly approved.
