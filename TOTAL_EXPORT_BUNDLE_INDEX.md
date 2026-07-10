# Total Export Bundle Index

Date: 2026-07-10

## Purpose

`total_export_bundle_index.py` defines a local-only helper for indexing existing Total Export review-bundle/package ZIP outputs and sibling sidecars.

It answers local review questions such as:

- Which ZIP files exist in a folder?
- Which `.sha256` sidecars exist next to those ZIPs?
- Which `.inspection.json` sidecars exist next to those ZIPs?
- What local ZIP size and SHA-256 metadata is available?
- Which local sidecars are missing, mismatched, or unreadable?

## Scope

This helper scans local files only. It does not extract ZIP files, read files from inside ZIPs, fetch sources, check archive services, submit archive URLs, download media, scrape pages, capture screenshots, transcribe, call providers, store credentials, or wire into the GUI.

Missing or mismatched sidecars are local follow-up signals only. They do not prove that a bundle is invalid or that external source content exists or does not exist.

## Inputs And Outputs

Inputs:

- A local root folder.
- Optional recursive scanning.
- Optional local ZIP hash computation.

Outputs:

- Per-ZIP local size and SHA-256 metadata.
- Sibling `.sha256` sidecar presence and hash-match status.
- Sibling `.inspection.json` sidecar presence/readability and a small JSON summary when present.
- Per-ZIP status, warnings, and recommended manual actions.
- Overall status counts.
- Deterministic text, Markdown, and dictionary/JSON-ready representations.

## Sidecar Expectations

The helper follows the current Total Export sidecar convention:

- ZIP SHA-256 sidecar: `<zip path>.sha256`
- ZIP inspection sidecar: `<zip path>.inspection.json`

SHA-256 sidecars may contain either:

- `<hash>`
- `<hash>  <filename>`

Inspection sidecars are parsed as local JSON only. The helper reads summary fields from the `zip_inspection` object when present.

## Status Meanings

- `complete`: ZIP, SHA-256 sidecar, matching hash, and readable inspection sidecar are present.
- `missing_sha256_sidecar`: The sibling `.sha256` sidecar is missing.
- `sha256_mismatch`: The sibling `.sha256` sidecar exists but does not match the local ZIP hash.
- `missing_inspection_sidecar`: The sibling `.inspection.json` sidecar is missing.
- `inspection_unreadable`: The sibling `.inspection.json` sidecar exists but cannot be parsed as the expected local JSON shape.
- `needs_review`: Reserved for local review states not covered by a more specific status.

## Safety Notes

- No ZIP extraction is performed.
- No downloads, source fetching, scraping, screenshots, archive checks/submission, transcription, provider calls, credential storage, or GUI behavior are performed.
- Future CLI integration should be a separate approved milestone and must remain local-only unless explicit behavior changes are approved later.
