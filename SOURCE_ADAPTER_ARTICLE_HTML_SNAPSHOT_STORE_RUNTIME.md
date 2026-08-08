# Source Adapter Article HTML Snapshot Store Runtime

This implementation milestone adds `source_adapter_article_html_snapshot_store_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers article HTML snapshot store rows for source URL, rendered HTML paths, screenshot digests, metadata extraction, and downstream evidence package inclusion.

The milestone preserves the `KEYS/ACCOUNTS` label, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

Tested status strings:

- `SOURCE_ADAPTER_ARTICLE_HTML_SNAPSHOT_STORE_RUNTIME_BUILT`
- `SOURCE_ADAPTER_ARTICLE_HTML_SNAPSHOT_STORE_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- `SOURCE_ADAPTER_ARTICLE_HTML_SNAPSHOT_STORE_RUNTIME_ROWS_READY`
