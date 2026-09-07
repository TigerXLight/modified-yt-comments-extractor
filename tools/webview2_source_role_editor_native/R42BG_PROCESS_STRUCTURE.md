# R42BG native WebView2 source-role editor process/database checkpoint

R42BF proved that the warm native WebView2 server is the right runtime path: the user recorded the editor opening in roughly one second, and the log showed command-to-first-role-paint under one second on the warmed path. R42BG keeps that path and does not move SQLite into the paint path.

## What changed in R42BG

- Keeps WebView2 warm-server startup and JSON-payload first paint.
- Removes stale document-start scripts when the warm helper is hidden back to about:blank.
- Makes the injected script return immediately on about:blank, so a hidden/warm blank page does not install the old toolbar/payload.
- Makes `server_command_to_first_role_paint` token-aware and useful-paint-aware; it now ignores old-token or zero-span blank events.
- Adds `native_schema` and `command_token` to role-change batches for cleaner DB inspection.
- Adds `role_plan_current`, a single current-plan table keyed by selected URL + mode + edit key. Historical payload sessions are still kept in `role_source_sessions` / `role_plan_rows`.
- Adds DB inspection buckets for all historical UI timings, latest 50 timings, and R42BG-only timings.

## Process decision

Do not switch to database/browser-GUI repos for page speed. Use WebView2Samples/WebView2Browser ideas for the host/runtime path and keep SQLite as a sidecar for durable review state, history, queues, and later source-role decisions.

## Current success criteria

- Cold app warm helper ready: about 1 second after app start.
- Open selected source from warm helper: about 1 second visually.
- Toggle Semantic/Media: near-instant synchronous switch with async media repaint.
- Text role click visual paint: near-instant; DB/log writes may arrive later.
- DB sync: compact old JSONL spam into useful events without touching raw JSONL.
