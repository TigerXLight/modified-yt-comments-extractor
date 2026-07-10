# Local Media Verification Report

This document describes the local-only media verification helper added for future preservation and Total Export workflows.

## Scope

- Verifies user-supplied local media records against current local filesystem state.
- Checks whether the recorded local path exists now.
- Compares current file size with recorded file size when a nonzero recorded size is available.
- Computes and compares SHA-256 only when `compute_hash=True`.
- Reports deterministic status, warnings, and recommended follow-up actions.

The helper does not download media, fetch source content, call APIs, inspect remote URLs, run ASR, probe media streams, archive pages, submit archive requests, scrape websites, launch browsers, or wire into the GUI.

## Statuses

- `verified`: local file exists, recorded size matches, and recorded SHA-256 matches.
- `missing_local_file`: the recorded local path does not currently point to a file.
- `size_mismatch`: the local file exists but current size differs from the recorded size.
- `sha256_mismatch`: the local file exists and size is acceptable, but current SHA-256 differs from the recorded SHA-256.
- `needs_review`: the local file exists, but verification is incomplete because recorded size/hash is missing or hash computation was disabled.
- `not_checked`: no meaningful local path was provided, so no file check was performed.

Blank or zero recorded size is treated as unknown metadata, not as a size mismatch. Blank recorded SHA-256 is treated as missing metadata, not as a hash mismatch.

## Hash Mode

When `compute_hash=True`, the helper reads the explicitly referenced local file and computes its SHA-256. When `compute_hash=False`, it does not read file bytes for hashing and reports hash comparison as needing review.

Local file size checks use filesystem metadata for the explicit local path in the record.

## Current-State Caution

Verification describes current local filesystem state only. A missing local file is a local preservation follow-up item; it is not proof that the original remote source is unavailable, deleted, changed, or inaccessible.

## Future Use

Future CLI or Total Export review flows can call this helper explicitly to re-check locally registered media records before building evidence bundles. Any such integration should remain opt-in and should keep verification separate from downloading, archive checks, ASR, browser automation, and source fetching.
