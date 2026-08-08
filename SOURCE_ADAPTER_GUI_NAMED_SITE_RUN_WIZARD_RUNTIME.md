# Source Adapter GUI Named-Site Run Wizard Runtime

This implementation milestone adds `source_adapter_gui_named_site_run_wizard_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers GUI named-site run wizard rows for source selection, approval metadata, capture profile selection, and dry/live receipt visibility.

The milestone preserves the `KEYS/ACCOUNTS` label, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

Tested status strings:

- `SOURCE_ADAPTER_GUI_NAMED_SITE_RUN_WIZARD_RUNTIME_BUILT`
- `SOURCE_ADAPTER_GUI_NAMED_SITE_RUN_WIZARD_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- `SOURCE_ADAPTER_GUI_NAMED_SITE_RUN_WIZARD_RUNTIME_ROWS_READY`
