# Manual Local Evidence Package Manifest

Date: 2026-07-10

## Purpose

`total_export_evidence_manifest.py` aggregates already-known local preservation metadata into a deterministic high-level manifest/report for future manual evidence-package review.

It can summarize represented sources/packages, manual archive records, local media records, local media verification statuses, preservation-plan follow-up, bundle-index items, and bundle reconciliation items.

## Local Metadata-Only Scope

The helper accepts in-memory objects from the existing local-only preservation helpers. It records counts, statuses, warnings, recommended actions, and local reference paths.

Local reference paths are metadata references only. The helper does not open, stat, hash, copy, move, package, or extract those paths. It creates no files, folders, ZIPs, or generated manifest artifacts.

The helper does not download or fetch sources, call network/API/archive services, scrape pages, automate browsers, capture screenshots, transcribe media, call providers, store credentials, inspect ZIP internals, or wire into the GUI.

## Supported Input Concepts

- Source URL strings.
- `ManualArchiveRecord` objects.
- `LocalMediaRecord` objects.
- Optional `LocalMediaVerificationResult`.
- Optional `PreservationPlanResult`.
- Optional `BundleIndexResult`.
- Optional `BundleIndexReconciliationResult`.

Source URLs use the existing pure-local preservation/YouTube normalization. Package IDs associate records only when an existing input supplies the mapping. Raw bundle-index items do not contain source/package identity, so they are represented as standalone local references instead of being guessed from filenames.

## Manifest Entries

Each `EvidenceManifestEntry` may include:

- Source URL and normalized URL.
- Package ID and optional local title.
- Archive and local media record counts/statuses.
- Local media verification statuses.
- Bundle index/reconciliation statuses.
- Local reference paths.
- Follow-up flag, warnings, and recommended actions.

`EvidenceManifestResult` includes overall entry, follow-up, archive, media, verification, and bundle-item counts plus deterministic entry, warning, and error collections.

## Follow-Up Meaning

An entry needs follow-up when an associated preservation-plan item, local media verification, or bundle reconciliation/index item needs review. Examples include:

- Missing manual archive metadata.
- Missing local media metadata or files.
- Size/hash mismatch or incomplete local verification.
- Missing expected bundle ZIPs.
- Unexpected bundles or bundle sidecar review states.

These are local review signals only. Missing local metadata/files do not prove remote deletion, unavailability, or invalidity.

## Report Functions

The helper provides deterministic dictionary, plain-text, and Markdown representations:

- `evidence_manifest_entry_to_dict()`
- `evidence_manifest_to_dict()`
- `build_evidence_manifest_text()`
- `build_evidence_manifest_markdown()`

No report is written automatically.

## Local CLI Usage

`total_export_evidence_manifest_cli.py` reads a local JSON object, builds the existing in-memory evidence manifest, and renders Markdown, text, or JSON.

```cmd
python total_export_evidence_manifest_cli.py --input EVIDENCE_MANIFEST_INPUT.json
python total_export_evidence_manifest_cli.py --input EVIDENCE_MANIFEST_INPUT.json --format text
python total_export_evidence_manifest_cli.py --input EVIDENCE_MANIFEST_INPUT.json --format json
python total_export_evidence_manifest_cli.py --input EVIDENCE_MANIFEST_INPUT.json --output EVIDENCE_MANIFEST_REPORT.md
python total_export_evidence_manifest_cli.py --input EVIDENCE_MANIFEST_INPUT.json --output EVIDENCE_MANIFEST_REPORT.md --overwrite
```

The input may include `source_urls`, `manual_archive_records`, `local_media_records`, `local_media_verification_items`, `bundle_reconciliation_items`, and `unexpected_bundle_reconciliation_items`. Local media paths are parsed with filesystem inspection and hashing disabled. Bundle items are reconstructed from supplied metadata only.

The CLI prints to stdout by default. It writes a file only when `--output` is explicitly supplied, and it preserves an existing output unless `--overwrite` is also supplied.

The CLI does not copy files, build packages, create or extract ZIPs, inspect ZIP internals, download or fetch sources, call network/API/archive services, scrape pages, capture screenshots, transcribe media, call providers, store credentials, or wire into the GUI.

## Future Integration

Package-builder integration requires a separate approved milestone. Package copying/building, ZIP creation/extraction, downloads, archive checks, network/provider calls, and GUI integration remain out of scope unless explicitly approved later.
