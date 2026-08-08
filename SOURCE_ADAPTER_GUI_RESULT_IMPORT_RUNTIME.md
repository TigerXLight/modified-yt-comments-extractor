# Source Adapter GUI Result Import Runtime

This implementation milestone adds `source_adapter_gui_result_import_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers GUI result import rows that surface provider receipts, archive results, failure triage, and review decisions.

The milestone preserves the `KEYS/ACCOUNTS` label, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

Tested status strings:

- `SOURCE_ADAPTER_GUI_RESULT_IMPORT_RUNTIME_BUILT`
- `SOURCE_ADAPTER_GUI_RESULT_IMPORT_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- `SOURCE_ADAPTER_GUI_RESULT_IMPORT_RUNTIME_ROWS_READY`
