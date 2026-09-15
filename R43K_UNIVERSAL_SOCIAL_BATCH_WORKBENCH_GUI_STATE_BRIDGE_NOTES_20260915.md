# R43K Universal Social Batch Workbench GUI State Bridge

Marker: `YTCE_R43K_UNIVERSAL_SOCIAL_BATCH_WORKBENCH_GUI_STATE_BRIDGE`

Status target: `PASS_R43K_UNIVERSAL_SOCIAL_BATCH_WORKBENCH_GUI_STATE_BRIDGE`

R43K adds a restore-only GUI/state bridge above the R43J universal social batch workbench panel. It persists and restores recent queue sessions, panel rows, selections, platform/status counts, action history, last inputs, and route receipt paths without routing or reprocessing completed work.

## Scope

- Saves panel-compatible state from existing R43J panel output.
- Restores R43J panel state while preserving selections and counts.
- Creates panel-compatible state snapshots from existing R43H queue files.
- Lists recent sessions with stable queue, panel, workbench, and receipt paths.
- Records last pasted/TXT-style inputs, selected queue ids, and receipt paths.
- Writes GUI state JSON/NDJSON/Markdown outputs and an R43K report.

## Delegation Boundary

R43K does not run, resume, retry, or route queue items. Those actions remain delegated to the existing chain:

`R43J -> R43I -> R43H -> R43G -> R43F -> R43E -> R43D`

Twitter/X remains the first concrete adapter; the state model is platform-neutral and preserves pending/unknown platform status for future Bluesky, Instagram, Facebook, Threads, Mastodon/Fediverse, TikTok, Reddit, YouTube, news comments, forums, and other social/comment adapters.

## Guardrails

R43K does not start WebView2 or CefSharp, copy browser internals, scrape hidden APIs, extract cookies/tokens, automate login, bypass CAPTCHA/challenges/paywalls/access controls, run source-role checks, invoke review-window loops or rewrites, remotely download media, or change YouTube capture engine behavior.

Machine URL/path fields stay plain strings, not Markdown-wrapped links.
