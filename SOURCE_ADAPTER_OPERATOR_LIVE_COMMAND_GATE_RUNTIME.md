# Source Adapter Operator Live Command Gate Runtime

This implementation milestone adds `source_adapter_operator_live_command_gate_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers operator live command gate rows for named-site command generation, explicit approval IDs, blocked auto-start behaviour, and copyable command runbooks.

The milestone preserves the `KEYS/ACCOUNTS` label, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

Tested status strings:

- `SOURCE_ADAPTER_OPERATOR_LIVE_COMMAND_GATE_RUNTIME_BUILT`
- `SOURCE_ADAPTER_OPERATOR_LIVE_COMMAND_GATE_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- `SOURCE_ADAPTER_OPERATOR_LIVE_COMMAND_GATE_RUNTIME_ROWS_READY`
