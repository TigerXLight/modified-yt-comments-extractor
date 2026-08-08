# Source Adapter Article Capture Runner Runtime

This implementation milestone adds `source_adapter_article_capture_runner_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers article capture runner rows for HTML snapshot, screenshot, archive request, normalized source evidence, and Total Export linkage.

The milestone preserves the `KEYS/ACCOUNTS` label, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

Tested status strings:

- `SOURCE_ADAPTER_ARTICLE_CAPTURE_RUNNER_RUNTIME_BUILT`
- `SOURCE_ADAPTER_ARTICLE_CAPTURE_RUNNER_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- `SOURCE_ADAPTER_ARTICLE_CAPTURE_RUNNER_RUNTIME_ROWS_READY`
