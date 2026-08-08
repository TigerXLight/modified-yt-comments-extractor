# Release Upload Target Runtime

Status: `SOURCE_ADAPTER_RELEASE_UPLOAD_TARGET_RUNTIME_BUILT`
Schema: `source_adapter_release_upload_target_runtime_v1`
Marker: `SOURCE_ADAPTER_RELEASE_UPLOAD_TARGET_RUNTIME`

## Purpose

This implementation adds the `release upload target` runtime surface for the shared source adapter pipeline. It is an implementation runtime module, not a placeholder note. It builds deterministic runtime rows, package identifiers, receipt requirements, verification output, and local persisted JSON artifacts that downstream GUI/controller/provider code can consume.

## Runtime coverage

- `local_folder`
- `github_release`
- `library_publish`
- `manual_handoff`

## KEYS/ACCOUNTS handling

The runtime keeps the user-facing label as `KEYS/ACCOUNTS`. Secret material is not serialized. Credential-related rows use redacted reference hashes only, so receipts and audit logs can identify which reference path was used without leaking key material.

## Operator execution model

The runtime is designed for explicit operator-controlled execution. Every row requires a receipt, every package verifies its own row counts and redaction state, and store/CLI/verifier tests exercise the same data shape used by the execution bundles.

## Implementation note

upload target rows prepare release and library destinations.
