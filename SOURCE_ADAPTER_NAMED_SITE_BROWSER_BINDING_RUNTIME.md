# Source Adapter Named-Site Browser Binding Runtime

This implementation milestone adds `source_adapter_named_site_browser_binding_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers named-site browser binding rows linking operator profile, browser driver, capture profile, and observation import readiness.

The milestone preserves the `KEYS/ACCOUNTS` label, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

Tested status strings:

- `SOURCE_ADAPTER_NAMED_SITE_BROWSER_BINDING_RUNTIME_BUILT`
- `SOURCE_ADAPTER_NAMED_SITE_BROWSER_BINDING_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- `SOURCE_ADAPTER_NAMED_SITE_BROWSER_BINDING_RUNTIME_ROWS_READY`
