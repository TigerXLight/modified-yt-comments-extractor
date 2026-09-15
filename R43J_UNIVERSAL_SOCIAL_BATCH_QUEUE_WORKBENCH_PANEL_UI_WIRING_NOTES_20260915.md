# R43J Universal Social Batch Queue Workbench Panel UI Wiring

Status target:
`PASS_R43J_UNIVERSAL_SOCIAL_BATCH_QUEUE_WORKBENCH_PANEL_UI_WIRING`

R43J exposes the R43I universal social batch queue workbench through a visible
panel model. It supports paste/load inputs, preview rows, row selection, platform
selection, run pending, resume, retry, skip, stop-after-current receipts, and
summary/route-receipt export.

Architecture:
- R43J panel actions delegate to R43I.
- R43I delegates queue work to R43H.
- R43H routes through R43G, R43F, and R43E before concrete adapters.
- Twitter/X remains the first concrete adapter only; pending social/comment
  platforms continue to receive mapped pending receipts.

Panel outputs:
`panel_state.json`, `panel_rows.ndjson`, `panel_actions.ndjson`,
`panel_selection.json`, `panel_summary.md`, `panel_receipt.json`,
workbench mirror files, route receipts, and the R43J report.

Boundary:
R43J does not start WebView2/CefSharp, copy browser internals, scrape hidden APIs,
extract cookies/tokens, automate login, bypass CAPTCHA/challenges/paywalls, run
source-role checks, invoke review-window loops, download remote media, or change
YouTube capture engine behavior.
