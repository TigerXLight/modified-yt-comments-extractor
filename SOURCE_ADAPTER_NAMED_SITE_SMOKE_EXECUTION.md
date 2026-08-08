# Source Adapter Named-Site Smoke Execution

This milestone implements a named-site smoke execution engine on top of the
operator-approved execution runtime and provider command runtime.  It is an
implementation slice: it constructs named-site smoke runs, executes the provider
command runtime, records per-site action receipts, writes an execution manifest,
and returns a verifier-ready package.

The engine is command-runtime backed.  Deterministic tests use local command
adapters; production callers can supply browser/archive/release/file-library
command adapters and KEYS/ACCOUNTS credential-reference lookup commands.

## Implemented surfaces

- Named-site smoke execution matrix for five adapter/source families.
- Provider-action execution receipts for credential lookup, browser capture,
  archive submission, release upload, and file-library publish.
- Per-site smoke summaries and an execution manifest.
- Store, CLI, verifier, and docs tests.

## Status strings

- `SOURCE_ADAPTER_NAMED_SITE_SMOKE_EXECUTION_BUILT`
- `SOURCE_ADAPTER_NAMED_SITE_SMOKE_EXECUTION_MATRIX_READY`
- `SOURCE_ADAPTER_NAMED_SITE_PROVIDER_ACTION_RECEIPTS_READY`
- `SOURCE_ADAPTER_NAMED_SITE_SMOKE_EXECUTION_READY_FOR_RECEIPT_REVIEW`

## Operator contract

A run is tied to operator approval rows and named-site inputs.  The runtime can
execute real provider command adapters when configured.  Receipts must preserve
`KEYS/ACCOUNTS` references and redacted hashes; raw secrets must not be written
into the receipt body.
