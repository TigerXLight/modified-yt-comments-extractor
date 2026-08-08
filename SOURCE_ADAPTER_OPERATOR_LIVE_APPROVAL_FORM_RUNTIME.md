# Source Adapter Operator Live Approval Form Runtime

This implementation milestone adds `source_adapter_operator_live_approval_form_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers operator live approval form rows for named sites, actions, provider accounts, risk notes, approval IDs, and explicit run/skip choices.

The milestone preserves the `KEYS/ACCOUNTS` label, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

Tested status strings:

- `SOURCE_ADAPTER_OPERATOR_LIVE_APPROVAL_FORM_RUNTIME_BUILT`
- `SOURCE_ADAPTER_OPERATOR_LIVE_APPROVAL_FORM_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- `SOURCE_ADAPTER_OPERATOR_LIVE_APPROVAL_FORM_RUNTIME_ROWS_READY`
