# Source Adapter X Twitter Profile Runtime

This implementation milestone adds `source_adapter_x_profile_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers X/Twitter profile rows for social post/thread capture, archive fallbacks, screenshot/manual evidence import, and receipt-safe source packaging.

The milestone preserves the `KEYS/ACCOUNTS` label, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

Tested status strings:

- `SOURCE_ADAPTER_X_PROFILE_RUNTIME_BUILT`
- `SOURCE_ADAPTER_X_PROFILE_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- `SOURCE_ADAPTER_X_PROFILE_RUNTIME_ROWS_READY`
