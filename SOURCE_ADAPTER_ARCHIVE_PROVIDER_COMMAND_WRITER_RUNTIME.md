# Source Adapter Archive Provider Command Writer Runtime

This implementation milestone adds `source_adapter_archive_provider_command_writer_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers archive provider command writer rows for archive.ph, Wayback, Ghostarchive, perma-like/manual commands, retry windows, and operator approval IDs.

The milestone preserves the `KEYS/ACCOUNTS` label, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

Tested status strings:

- `SOURCE_ADAPTER_ARCHIVE_PROVIDER_COMMAND_WRITER_RUNTIME_BUILT`
- `SOURCE_ADAPTER_ARCHIVE_PROVIDER_COMMAND_WRITER_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- `SOURCE_ADAPTER_ARCHIVE_PROVIDER_COMMAND_WRITER_RUNTIME_ROWS_READY`
