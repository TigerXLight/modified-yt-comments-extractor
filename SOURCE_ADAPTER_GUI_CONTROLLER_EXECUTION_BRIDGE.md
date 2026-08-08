# Source Adapter GUI Controller Execution Bridge

Status: `SOURCE_ADAPTER_GUI_CONTROLLER_EXECUTION_BRIDGE_BUILT`

This milestone implements the GUI/controller execution bridge that connects operator-approved runtime rows and provider backend interface rows to callable route dispatch receipts. The handoff status is `SOURCE_ADAPTER_GUI_CONTROLLER_EXECUTION_BRIDGE_READY_FOR_UI_BUTTON_AND_PROVIDER_BACKEND_REPLACEMENT`.

## Implemented route surfaces

- `source_adapter.gui.runtime.action_palette`
- `source_adapter.gui.priority_fixture_pack_runner`
- `source_adapter.gui.live_smoke_receipt_capture`
- `keys_accounts.gui.credential_reference_selector`

The `KEYS/ACCOUNTS` credential-reference selector is preserved, and the future Online ASR button requirement remains in scope for the concrete GUI binding patch.

## Implemented behavior

The bridge registers four GUI/controller routes and records five dispatch receipts for the named-site execution rows. It links the operator-approved runtime and provider-backend interface packages so UI button binding and provider-specific backend replacement can be implemented next.
