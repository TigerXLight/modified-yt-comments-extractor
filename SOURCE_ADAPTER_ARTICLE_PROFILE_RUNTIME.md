# Source Adapter Article Profile Runtime

This implementation milestone adds `source_adapter_article_profile_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers generic article profile rows for page HTML, screenshot, source metadata, archive routing, evidence claim links, and release package inclusion.

The milestone preserves the `KEYS/ACCOUNTS` label, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

Tested status strings:

- `SOURCE_ADAPTER_ARTICLE_PROFILE_RUNTIME_BUILT`
- `SOURCE_ADAPTER_ARTICLE_PROFILE_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- `SOURCE_ADAPTER_ARTICLE_PROFILE_RUNTIME_ROWS_READY`
