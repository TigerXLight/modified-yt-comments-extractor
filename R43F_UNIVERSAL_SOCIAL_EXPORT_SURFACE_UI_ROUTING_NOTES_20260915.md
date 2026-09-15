# R43F Universal Social Export Surface UI Routing Notes

Status target: `PASS_R43F_UNIVERSAL_SOCIAL_EXPORT_SURFACE_UI_ROUTING`

R43F adds a platform-neutral UI/export routing surface above the R43E universal social account tracking registry. It accepts account tracking requests using universal fields and resolves the platform through the R43E adapter map first.

Twitter/X dispatches to the existing R43D export surface through R43E. Bluesky, Instagram, Facebook, Threads, Mastodon, TikTok, Reddit, YouTube, and news comments return mapped pending-adapter receipts. Unknown platforms return unsupported-platform receipts.

The router preserves the universal output contract:

- `account_record.md`
- `account_timeline.ndjson`
- `media_index.json`
- `progress_events.ndjson`
- `screenshot_receipts_index.json`
- `account_tracking_request.json`
- `account_tracking_runbook.md`
- `account_tracking_surface_receipt.json`
- `adapter_map.json`
- `universal_routing_receipt.json`

Boundaries preserved:

- WebView2, CefSharp, and manual import are observation feeds only.
- R43F does not start WebView2 or copy WebView2 internals.
- No cookie/token extraction.
- No hidden X API scraping.
- No CAPTCHA/challenge bypass.
- No source-role checks or review-window dependency.
- No remote media downloads.
