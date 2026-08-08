# Source Adapter X Reply Thread Archive Ticket Runtime

This implementation milestone adds `source_adapter_x_reply_thread_archive_ticket_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers X/Twitter reply thread archive ticket rows for reply URLs, nested thread evidence, fallback archive receipts, manual review gates, and evidence claim mapping.

The milestone preserves the `KEYS/ACCOUNTS` label, keeps Online ASR adjacent to Local ASR in the runtime contract, preserves the local `whisper.cpp large-v3 Vulkan on AMD RX 5700` profile, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

- Status marker: `SOURCE_ADAPTER_X_REPLY_THREAD_ARCHIVE_TICKET_RUNTIME_BUILT`
- Handoff marker: `SOURCE_ADAPTER_X_REPLY_THREAD_ARCHIVE_TICKET_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- Row status marker: `SOURCE_ADAPTER_X_REPLY_THREAD_ARCHIVE_TICKET_RUNTIME_ROWS_READY`
