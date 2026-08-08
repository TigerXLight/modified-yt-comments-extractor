# Source Adapter MSN Profile Runtime

This implementation milestone adds `source_adapter_msn_profile_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers MSN profile rows for Android user-agent capture, comment shadow-root handling, overlay containers, manual observation imports, and archive/evidence linkage.

The milestone preserves the `KEYS/ACCOUNTS` label, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

Tested status strings:

- `SOURCE_ADAPTER_MSN_PROFILE_RUNTIME_BUILT`
- `SOURCE_ADAPTER_MSN_PROFILE_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- `SOURCE_ADAPTER_MSN_PROFILE_RUNTIME_ROWS_READY`
