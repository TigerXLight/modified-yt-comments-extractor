# R43I Universal Social Batch Queue Workbench Controls

Status target:
`PASS_R43I_UNIVERSAL_SOCIAL_BATCH_QUEUE_WORKBENCH_CONTROLS`

R43I adds a workbench/control surface above the R43H persistent universal social
batch queue. It supports queue preview, existing queue loading, run pending,
resume, retry failed-retryable rows, retry selected rows, skip selected rows,
stop-after-current receipt generation, queue summary export, and route receipt
export.

The workbench row model remains platform-neutral and preserves:
`queue_id`, `batch_index`, raw and normalized URL fields, `platform_id`,
`url_kind`, `account_handle`, `record_id`, `dedupe_key`, `duplicate_of`,
status fields, attempts, selection flags, run/retry eligibility, errors, receipt
path, run directory, and update timestamp.

Routing boundary:
- Queue preview does not route items.
- Run/resume/retry operations delegate to R43H.
- R43H delegates detection/routing through R43G, R43F, and R43E before concrete
  adapters such as the current Twitter/X R43D adapter.
- Duplicate rows remain visible and are not routed twice.
- Pending platform and unknown platform receipts remain visible as receipts, not
  crashes.

Side-effect boundary:
R43I does not start WebView2/CefSharp, copy browser internals, scrape hidden
APIs, extract cookies/tokens, automate login, bypass challenges/paywalls, run
source-role checks, invoke review-window loops, download remote media, or change
YouTube capture engine behavior.
