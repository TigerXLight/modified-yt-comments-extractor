# Live Smoke Readiness Runtime

Status: `SOURCE_ADAPTER_LIVE_SMOKE_READINESS_RUNTIME_BUILT`
Schema: `source_adapter_live_smoke_readiness_runtime_v1`
Marker: `SOURCE_ADAPTER_LIVE_SMOKE_READINESS_RUNTIME`

## Purpose

This implementation adds the `live smoke readiness` runtime surface for the shared source adapter pipeline. It is an implementation runtime module, not a placeholder note. It builds deterministic runtime rows, package identifiers, receipt requirements, verification output, and local persisted JSON artifacts that downstream GUI/controller/provider code can consume.

## Runtime coverage

- `named_site_profile`
- `approval_packet`
- `provider_health`
- `rollback_plan`

## KEYS/ACCOUNTS handling

The runtime keeps the user-facing label as `KEYS/ACCOUNTS`. Secret material is not serialized. Credential-related rows use redacted reference hashes only, so receipts and audit logs can identify which reference path was used without leaking key material.

## Operator execution model

The runtime is designed for explicit operator-controlled execution. Every row requires a receipt, every package verifies its own row counts and redaction state, and store/CLI/verifier tests exercise the same data shape used by the execution bundles.

## Implementation note

readiness rows check approvals, named-site profiles, provider health, and rollback state.
