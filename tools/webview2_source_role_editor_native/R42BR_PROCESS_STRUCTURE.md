# R42BR Process Structure

R42BR keeps the R42BO native toolbar behaviour but fixes the layout: the toolbar and WebView2 are hosted in a two-row native TableLayoutPanel, so the YTCE controls cannot overlay the rendered page or Wayback capture banner.

Kept from prior patches:
- warm WebView2 server path
- source dropdown navigation
- instant role/mode click path
- SQLite sidecar sync, compact import, current-state table, and maintenance commands

R42BR UI cleanup:
- toolbar row is a native host row, not a page overlay
- WebView2 starts below the toolbar row
- icon/emoji buttons are replaced with stable text labels
- URL label hides on narrow windows to avoid crushed controls


R42BR note: native toolbar remains in a separate WinForms row above WebView2, but the action buttons now load the project PNG icons from assets/profile_media/source_roles instead of drawing vector placeholders. This keeps Wayback visible while restoring the original copy/link/external icon look.
