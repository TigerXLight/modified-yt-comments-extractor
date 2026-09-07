# R42ED — Semantic/media logic comprehension matrix + text-colouring cleanup

R42EC closed the archive role-display bug. R42ED starts the next workstream without re-hitting archive.ph.

## What this patch does

- Adds a no-GUI/no-network semantic/media role-comprehension matrix.
- Adds an adapter guard matrix for R42DI–R42DM:
  - R42DI: OpenClaw/Camoufox source-material adapter bridge.
  - R42DJ: web/source discovery provider fallbacks; discovery only, not silent substitution.
  - R42DK: media/document/export fallback.
  - R42DL: diagnostics/dev support.
  - R42DM: optional account/channel/device adapters; explicit user action only.
- Adds payload metadata so R42DW archive role payloads carry role-comprehension, colour-theme, and adapter-guard metadata.
- Cleans native WebView2 role-colour CSS by defining the variables used by recolour mode and adding role labels/tooltips to painted spans.

## Safety boundary

The probes do not open the project app, do not open WebView2, do not hit archive.ph, do not start Tor/Camoufox, do not call OpenClaw, and do not poll accounts/channels/devices.

## Closeout expectation

Expected no-GUI probe verdict:

```json
{
  "semantic_counts_nonzero": true,
  "media_counts_nonzero": true,
  "role_colour_cleanup_defined": true,
  "comprehension_matrix_defined": true,
  "adapter_guard_matrix_covers_r42di_to_r42dm": true,
  "discovery_fallbacks_are_not_silent_substitution": true,
  "account_channel_device_adapters_explicit_only": true,
  "no_gui_no_network_safe": true
}
```
