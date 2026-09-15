# R43B Twitter/X Account Timeline Runner With Progress/Pause/Recovery

Marker: `YTCE_R43B_TWITTER_X_ACCOUNT_TIMELINE_RUNNER_PROGRESS_PAUSE_RECOVERY`

Status target: `PASS_R43B_TWITTER_X_ACCOUNT_TIMELINE_RUNNER_PROGRESS_PAUSE_RECOVERY`

R43B adds the Twitter/X whole-account timeline runner shell after R43A.

## Purpose

- Run a whole-account capture shell for posts, reposts, quotes, screenshots, and media receipts.
- Track progress in `timeline_progress_events.ndjson`.
- Represent dynamic pause/recovery for rate-limit or platform-backpressure states.
- Feed normalized timeline records into the R43A account media ledger/date-folder export map.
- Preserve the user's requested folder model: account-level record document, date folders, per-post/repost folders, static screenshot receipt, and media subfolders.

## WebView2 boundary

WebView2 is only the site-rendering and observation input. R43B keeps tracking, dedupe, manifest writing, screenshots, folder routing, progress, privacy flags, and ledger export in the local Python/app layer.

R43B does not depend on the review/source-role WebView2 lane, does not call source-role checks, and does not use review-window back-and-forth behavior.

## Hard boundaries

- No hidden X API scraping.
- No cookie or token extraction.
- No CAPTCHA/challenge bypass.
- No access-control bypass.
- No remote media download in the timeline runner.
- No source-role assignment.
- No review-window rewrite.
- No YouTube capture-engine change.

## Validation

The patch validates R43B plus the current R43A/R42GZ/R42GY/R42GW/R42GX/R42GV media stack.
