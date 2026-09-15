# R43L Universal Social Batch Workbench App Shell Commands

Marker: `YTCE_R43L_UNIVERSAL_SOCIAL_BATCH_WORKBENCH_APP_SHELL_COMMANDS`

Status target: `PASS_R43L_UNIVERSAL_SOCIAL_BATCH_WORKBENCH_APP_SHELL_COMMANDS`

R43L adds a narrow app-shell command/navigation layer above the existing R43J workbench panel and R43K GUI state bridge. It exposes app-level commands for opening the universal social batch workbench, pasting/loading inputs, previewing queues, saving/restoring GUI state, preserving recent sessions and selections, running/resuming/retrying/skipping selected rows, and exporting summaries/route receipts.

## Delegation

R43L delegates panel and queue-visible commands to R43J and GUI state commands to R43K. It does not call R43H, R43G, R43F, R43E, or R43D directly. When processed, the route chain remains:

`R43L -> R43J/R43K -> R43I -> R43H -> R43G -> R43F -> R43E -> R43D`

Twitter/X remains only the first concrete adapter. The command result model is platform-neutral and keeps pending/unknown platform receipts visible for future adapters.

## Outputs

The app-shell writes `app_shell_state.json`, command/result NDJSON, navigation and selection JSON, recent sessions, summary/receipt files, delegated panel/GUI state snapshots, route receipts, and R43L report JSON/Markdown.

## Guardrails

R43L does not start WebView2 or CefSharp, copy browser internals, scrape hidden APIs, extract cookies/tokens, automate login, bypass CAPTCHA/challenges/paywalls/access controls, run source-role checks, invoke review-window loops or rewrites, remotely download media, or change YouTube capture engine behavior.

Machine URL/path fields remain plain strings, not Markdown-wrapped links.
