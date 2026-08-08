# Evidence Item Materialization Runtime

Status: `SOURCE_ADAPTER_EVIDENCE_ITEM_MATERIALIZATION_RUNTIME_BUILT`
Schema: `source_adapter_evidence_item_materialization_runtime_v1`
Marker: `SOURCE_ADAPTER_EVIDENCE_ITEM_MATERIALIZATION_RUNTIME`

## Purpose

This implementation adds the `evidence item materialization` runtime surface for the shared source adapter pipeline. It is an implementation runtime module, not a placeholder note. It builds deterministic runtime rows, package identifiers, receipt requirements, verification output, and local persisted JSON artifacts that downstream GUI/controller/provider code can consume.

## Runtime coverage

- `source_item`
- `claim_link`
- `artifact_ref`
- `review_state`

## KEYS/ACCOUNTS handling

The runtime keeps the user-facing label as `KEYS/ACCOUNTS`. Secret material is not serialized. Credential-related rows use redacted reference hashes only, so receipts and audit logs can identify which reference path was used without leaking key material.

## Operator execution model

The runtime is designed for explicit operator-controlled execution. Every row requires a receipt, every package verifies its own row counts and redaction state, and store/CLI/verifier tests exercise the same data shape used by the execution bundles.

## Implementation note

evidence rows materialize source artifacts into reviewable evidence items.
