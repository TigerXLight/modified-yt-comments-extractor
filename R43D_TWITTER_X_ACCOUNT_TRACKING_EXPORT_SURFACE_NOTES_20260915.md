# R43D — Twitter/X Account Tracking Export Surface

Marker: `YTCE_R43D_TWITTER_X_ACCOUNT_TRACKING_EXPORT_SURFACE`

Status target: `PASS_R43D_TWITTER_X_ACCOUNT_TRACKING_EXPORT_SURFACE`

## Scope

R43D adds the user-facing account tracking export surface above R43B/R43A/R43C.

It accepts a Twitter/X account URL or handle and records a concrete local export job for:

- posts
- reposts
- quote posts
- optional replies
- media-bearing records
- static screenshots
- screenshot materialization receipts
- date-folder account ledger output

## Architecture

WebView2 remains an optional site-rendering/observation engine below the account runner.

Tracking, dedupe, ledger writing, folder routing, screenshot receipt status, media index creation, progress event linking, and account-record output live in the local Python/app layer.

The surface does not copy WebView2 internals and does not require the review/source-role WebView2 lane.

## Output contract

The surface writes:

- `account_tracking_request.json`
- `account_tracking_runbook.md`
- `account_tracking_surface_receipt.json`
- R43B timeline runner outputs
- R43A `account_record.md`, `manifest.json`, date folders, media index
- R43C screenshot receipt index and per-post receipt files

## Safety and boundary flags

- no hidden X API scraping
- no cookie/token extraction
- no CAPTCHA/challenge bypass
- no remote media download in this surface
- no source-role checks
- no source-role assignment
- no review-window rewrite
- no YouTube capture-engine change
