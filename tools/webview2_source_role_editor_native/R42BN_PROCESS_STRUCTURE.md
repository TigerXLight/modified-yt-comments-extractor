# R42BN process structure

R42BN keeps the R42BI/R42BK/R42BM structure:

- Warm WebView2 helper process for speed.
- JSON payload for first paint.
- SQLite sidecar for durable/current state, compact history, inspection, and manual maintenance.
- JSONL remains the raw append-only audit.
- Source dropdown navigation happens inside the existing editor window.

R42BN fixes the archive-page toolbar layout by keeping the YTCE toolbar at the top while reserving a larger archive safe area and directly offsetting Wayback banner elements such as `#wm-ipp-base` / `#wm-ipp`. This avoids covering the Wayback capture/date banner and keeps the page content below both the YTCE toolbar and the archive banner.
