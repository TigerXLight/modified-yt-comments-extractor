# Source Adapter MSN Shadow Comment Ticket Runtime

This implementation milestone adds `source_adapter_msn_shadow_comment_ticket_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers MSN shadow comment ticket rows for social-comment-wc shadow roots, overlay-container capture, comment/reply tree materialization, and selector verification.

The milestone preserves the `KEYS/ACCOUNTS` label, keeps Online ASR adjacent to Local ASR in the runtime contract, preserves the local `whisper.cpp large-v3 Vulkan on AMD RX 5700` profile, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

- Status marker: `SOURCE_ADAPTER_MSN_SHADOW_COMMENT_TICKET_RUNTIME_BUILT`
- Handoff marker: `SOURCE_ADAPTER_MSN_SHADOW_COMMENT_TICKET_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- Row status marker: `SOURCE_ADAPTER_MSN_SHADOW_COMMENT_TICKET_RUNTIME_ROWS_READY`
