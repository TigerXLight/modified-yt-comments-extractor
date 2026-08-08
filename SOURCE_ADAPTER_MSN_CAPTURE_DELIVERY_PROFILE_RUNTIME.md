# Source Adapter MSN Capture Delivery Profile Runtime

This implementation milestone adds `source_adapter_msn_capture_delivery_profile_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers MSN capture delivery profile rows for Firefox RDM Android UA, social-comment-wc shadow roots, overlay-container scrolling, and manual observation receipts.

The milestone preserves the `KEYS/ACCOUNTS` label, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

Tested status strings:

- `SOURCE_ADAPTER_MSN_CAPTURE_DELIVERY_PROFILE_RUNTIME_BUILT`
- `SOURCE_ADAPTER_MSN_CAPTURE_DELIVERY_PROFILE_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- `SOURCE_ADAPTER_MSN_CAPTURE_DELIVERY_PROFILE_RUNTIME_ROWS_READY`
