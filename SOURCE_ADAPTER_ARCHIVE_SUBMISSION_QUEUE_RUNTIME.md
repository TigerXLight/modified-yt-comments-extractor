# Archive Submission Queue Runtime

Status: `SOURCE_ADAPTER_ARCHIVE_SUBMISSION_QUEUE_RUNTIME_BUILT`
Schema: `source_adapter_archive_submission_queue_runtime_v1`
Marker: `SOURCE_ADAPTER_ARCHIVE_SUBMISSION_QUEUE_RUNTIME`

## Purpose

This implementation adds the `archive submission queue` runtime surface for the shared source adapter pipeline. It is an implementation runtime module, not a placeholder note. It builds deterministic runtime rows, package identifiers, receipt requirements, verification output, and local persisted JSON artifacts that downstream GUI/controller/provider code can consume.

## Runtime coverage

- `archive_ph`
- `wayback`
- `ghostarchive`
- `manual_local_files`

## KEYS/ACCOUNTS handling

The runtime keeps the user-facing label as `KEYS/ACCOUNTS`. Secret material is not serialized. Credential-related rows use redacted reference hashes only, so receipts and audit logs can identify which reference path was used without leaking key material.

## Operator execution model

The runtime is designed for explicit operator-controlled execution. Every row requires a receipt, every package verifies its own row counts and redaction state, and store/CLI/verifier tests exercise the same data shape used by the execution bundles.

## Implementation note

archive queue rows organize provider submissions and pending result polling.
