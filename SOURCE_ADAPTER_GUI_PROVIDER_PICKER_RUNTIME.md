# Source Adapter GUI Provider Picker Runtime

This implementation milestone adds `source_adapter_gui_provider_picker_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers GUI provider picker rows for added providers, provider catalogue search, availability, and KEYS/ACCOUNTS references.

The milestone preserves the `KEYS/ACCOUNTS` label, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

Tested status strings:

- `SOURCE_ADAPTER_GUI_PROVIDER_PICKER_RUNTIME_BUILT`
- `SOURCE_ADAPTER_GUI_PROVIDER_PICKER_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- `SOURCE_ADAPTER_GUI_PROVIDER_PICKER_RUNTIME_ROWS_READY`
