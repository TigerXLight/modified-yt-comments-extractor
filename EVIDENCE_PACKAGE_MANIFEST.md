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

## Future Integration

A CLI or package-builder integration requires a separate approved milestone. Any future CLI should preserve explicit-output-only writes. Package copying/building, ZIP extraction, downloads, archive checks, network/provider calls, and GUI integration remain out of scope unless explicitly approved later.
