# Source Adapter GUI KEYS Accounts Ticket Runtime

This implementation milestone adds `source_adapter_gui_keys_accounts_ticket_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers GUI KEYS/ACCOUNTS ticket rows for added-provider windows, Add Provider panel state, catalogue search, visible provider cards, and credential boundary warnings.

The milestone preserves the `KEYS/ACCOUNTS` label, keeps Online ASR adjacent to Local ASR in the runtime contract, preserves the local `whisper.cpp large-v3 Vulkan on AMD RX 5700` profile, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

- Status marker: `SOURCE_ADAPTER_GUI_KEYS_ACCOUNTS_TICKET_RUNTIME_BUILT`
- Handoff marker: `SOURCE_ADAPTER_GUI_KEYS_ACCOUNTS_TICKET_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- Row status marker: `SOURCE_ADAPTER_GUI_KEYS_ACCOUNTS_TICKET_RUNTIME_ROWS_READY`
