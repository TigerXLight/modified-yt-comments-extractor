# Provider Capability Registry Runtime

Status: `SOURCE_ADAPTER_PROVIDER_CAPABILITY_REGISTRY_RUNTIME_BUILT`
Schema: `source_adapter_provider_capability_registry_runtime_v1`
Marker: `SOURCE_ADAPTER_PROVIDER_CAPABILITY_REGISTRY_RUNTIME`

## Purpose

This implementation adds the `provider capability registry` runtime surface for the shared source adapter pipeline. It is an implementation runtime module, not a placeholder note. It builds deterministic runtime rows, package identifiers, receipt requirements, verification output, and local persisted JSON artifacts that downstream GUI/controller/provider code can consume.

## Runtime coverage

- `browser_capture`
- `archive_submit`
- `release_upload`
- `file_library_publish`
- `credential_lookup`

## KEYS/ACCOUNTS handling

The runtime keeps the user-facing label as `KEYS/ACCOUNTS`. Secret material is not serialized. Credential-related rows use redacted reference hashes only, so receipts and audit logs can identify which reference path was used without leaking key material.

## Operator execution model

The runtime is designed for explicit operator-controlled execution. Every row requires a receipt, every package verifies its own row counts and redaction state, and store/CLI/verifier tests exercise the same data shape used by the execution bundles.

## Implementation note

capability registry rows expose provider capabilities to GUI and controller layers.
