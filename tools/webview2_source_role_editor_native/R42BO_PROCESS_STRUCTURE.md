# R42BO process structure

R42BO keeps the R42BI/R42BK database and source-navigation structure, but changes the toolbar placement model.

- Warm WebView2 helper process stays in use for speed.
- JSON payload still drives first paint.
- SQLite sidecar still stores current state, compact history, inspection, and manual maintenance.
- JSONL remains the raw append-only audit trail.
- Source dropdown navigation still happens inside the existing editor window.
- The YTCE toolbar is now a native WinForms toolbar docked above the WebView2 control.
- The injected DOM toolbar is hidden and kept only as a lightweight bridge/state helper.

This means Wayback, archive.ph, and the live article render in the WebView2 area below the toolbar. The editor toolbar no longer overlays or covers the rendered webpage, so Wayback's capture/date banner should remain visible at the top of the page.
