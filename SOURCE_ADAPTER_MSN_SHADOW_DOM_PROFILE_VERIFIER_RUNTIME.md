# Source Adapter MSN Shadow DOM Profile Verifier Runtime

This implementation milestone adds `source_adapter_msn_shadow_dom_profile_verifier_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers MSN shadow-DOM profile verifier rows for Android user-agent notes, social-comment-wc host selection, overlay container scrolling, and manual observation parity.

The milestone preserves the `KEYS/ACCOUNTS` label, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

Tested status strings:

- `SOURCE_ADAPTER_MSN_SHADOW_DOM_PROFILE_VERIFIER_RUNTIME_BUILT`
- `SOURCE_ADAPTER_MSN_SHADOW_DOM_PROFILE_VERIFIER_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- `SOURCE_ADAPTER_MSN_SHADOW_DOM_PROFILE_VERIFIER_RUNTIME_ROWS_READY`
