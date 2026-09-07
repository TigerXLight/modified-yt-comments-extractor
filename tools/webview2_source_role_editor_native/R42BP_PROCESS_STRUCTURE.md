# R42BP Process Structure

R42BP keeps the R42BO native toolbar behaviour but fixes the layout: the toolbar and WebView2 are hosted in a two-row native TableLayoutPanel, so the YTCE controls cannot overlay the rendered page or Wayback capture banner.

Kept from prior patches:
- warm WebView2 server path
- source dropdown navigation
- instant role/mode click path
- SQLite sidecar sync, compact import, current-state table, and maintenance commands

R42BP UI cleanup:
- toolbar row is a native host row, not a page overlay
- WebView2 starts below the toolbar row
- icon/emoji buttons are replaced with stable text labels
- URL label hides on narrow windows to avoid crushed controls
