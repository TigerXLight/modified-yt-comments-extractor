# R43H Universal Social Batch Queue Resume Dedupe Progress

Status target:
`PASS_R43H_UNIVERSAL_SOCIAL_BATCH_QUEUE_RESUME_DEDUPE_PROGRESS`

R43H adds a persistent platform-neutral batch queue above the R43G intake detector
and the R43F/R43E universal routing chain. Twitter/X remains only the first
implemented concrete adapter. Bluesky, Instagram, Facebook, Threads, Mastodon,
TikTok, Reddit, YouTube, and news comments continue to produce mapped pending
receipts where their concrete adapters are not implemented.

Queue records keep the required neutral fields:
`queue_id`, `batch_index`, `raw_input`, `normalized_url`, `platform_id`,
`url_kind`, `account_handle`, `record_id`, `dedupe_key`, `route_status`,
`downstream_status`, `status`, `attempts`, timestamps, errors, receipt path, and
run directory.

Dedupe policy:
- Exact normalized URL duplicates collapse within the same platform.
- `platform_id + account_handle + record_id` duplicates collapse when a record ID
  exists.
- Different platforms are not merged.
- Account URLs are not merged with post/comment URLs unless a record key proves
  the same record.
- Duplicate rows remain visible with `duplicate_of` and are not routed twice.

Resume policy:
- Completed items are skipped.
- Pending and failed-retryable items are eligible for routing.
- Failed-terminal and unsupported-platform items are skipped unless forced.
- Previous queue rows and route receipts are preserved in the resume receipt.

Boundary:
R43H does not start WebView2 or CefSharp, copy browser internals, scrape hidden
APIs, extract cookies/tokens, automate login, bypass CAPTCHA/challenges/paywalls,
run source-role checks, invoke review-window loops, download remote media, or
change YouTube capture engine behavior.
