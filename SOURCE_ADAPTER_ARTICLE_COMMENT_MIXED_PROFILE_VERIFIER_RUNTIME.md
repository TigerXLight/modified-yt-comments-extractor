# Source Adapter Article Comment Mixed Profile Verifier Runtime

This implementation milestone adds `source_adapter_article_comment_mixed_profile_verifier_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers article/comment mixed profile verifier rows for pages with embedded comments, article snapshots, comment extraction, archive fallback, and combined evidence packaging.

The milestone preserves the `KEYS/ACCOUNTS` label, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

Tested status strings:

- `SOURCE_ADAPTER_ARTICLE_COMMENT_MIXED_PROFILE_VERIFIER_RUNTIME_BUILT`
- `SOURCE_ADAPTER_ARTICLE_COMMENT_MIXED_PROFILE_VERIFIER_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- `SOURCE_ADAPTER_ARTICLE_COMMENT_MIXED_PROFILE_VERIFIER_RUNTIME_ROWS_READY`
