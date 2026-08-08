# Source Adapter Provider Command Runtime

This milestone adds an executable provider-command runtime for source adapters.
It is implementation code, not a planning-only checklist.  The runtime accepts
operator-approved provider command rows, executes configured local command
adapters, captures stdout/stderr/exit status, writes receipt JSON, and records
redacted credential-reference metadata.

The default examples use deterministic local Python commands so the test suite
can run without network credentials.  Production/provider-specific callers can
supply command templates for browser capture, archive submission, release
upload, file-library publish, and KEYS/ACCOUNTS credential-reference lookup.
The same receipt schema is used for deterministic local tests and real provider
command adapters.

## Implemented surfaces

- Provider command request matrix from operator-approved execution runtime rows.
- Executable command runner with timeout, cwd, env allow-list, and redaction.
- Receipt writer for every command execution.
- Store, CLI, verifier, and docs tests.
- Secret-material checks: command receipts preserve redacted references and do
  not store raw credential material.

## Status strings

- `SOURCE_ADAPTER_PROVIDER_COMMAND_RUNTIME_BUILT`
- `SOURCE_ADAPTER_PROVIDER_COMMAND_REQUEST_MATRIX_READY`
- `SOURCE_ADAPTER_PROVIDER_COMMAND_EXECUTION_RECEIPTS_READY`
- `SOURCE_ADAPTER_PROVIDER_COMMAND_RUNTIME_READY_FOR_NAMED_SITE_SMOKE_EXECUTION`

## Operator contract

The runtime can execute real provider command adapters when an operator supplies
explicit command configuration and input references.  Tests use local commands
only.  Real provider configurations should pass credential references through
`KEYS/ACCOUNTS` and receipt logs should contain redacted hashes, not secret
values.
