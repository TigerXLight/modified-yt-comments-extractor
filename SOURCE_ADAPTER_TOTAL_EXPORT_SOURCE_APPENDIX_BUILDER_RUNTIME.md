# Source Adapter Total Export Source Appendix Builder Runtime

This implementation milestone adds `source_adapter_total_export_source_appendix_builder_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers Total Export source appendix builder rows for article/comment/media/archive receipts, digests, claims, source metadata, and export manifest references.

The milestone preserves the `KEYS/ACCOUNTS` label, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

Tested status strings:

- `SOURCE_ADAPTER_TOTAL_EXPORT_SOURCE_APPENDIX_BUILDER_RUNTIME_BUILT`
- `SOURCE_ADAPTER_TOTAL_EXPORT_SOURCE_APPENDIX_BUILDER_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- `SOURCE_ADAPTER_TOTAL_EXPORT_SOURCE_APPENDIX_BUILDER_RUNTIME_ROWS_READY`
