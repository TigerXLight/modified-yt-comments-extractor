# Source Adapter X Archive Delivery Profile Runtime

This implementation milestone adds `source_adapter_x_archive_delivery_profile_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers X/Twitter archive delivery profile rows for post/thread URLs, screenshots, archive fallback providers, ghost/perma/manual imports, and evidence packaging.

The milestone preserves the `KEYS/ACCOUNTS` label, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

Tested status strings:

- `SOURCE_ADAPTER_X_ARCHIVE_DELIVERY_PROFILE_RUNTIME_BUILT`
- `SOURCE_ADAPTER_X_ARCHIVE_DELIVERY_PROFILE_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- `SOURCE_ADAPTER_X_ARCHIVE_DELIVERY_PROFILE_RUNTIME_ROWS_READY`
