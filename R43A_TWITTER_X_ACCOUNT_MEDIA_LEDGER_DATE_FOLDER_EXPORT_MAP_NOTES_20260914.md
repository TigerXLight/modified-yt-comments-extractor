# R43A Twitter/X Account Media Ledger And Date-Folder Export Map

Marker: `YTCE_R43A_TWITTER_X_ACCOUNT_MEDIA_LEDGER_DATE_FOLDER_EXPORT_MAP`
Status: implemented by local patch script, then validated by tests/report.

## Purpose

R43A adds the account-level export ledger requested for whole Twitter/X account captures.

It writes a single whole-account document with directional links into date folders and per-post/per-repost media folders:

```text
source_exports/twitter_x/<handle>/account_capture_<timestamp>/
  manifest.json
  account_record.md
  account_timeline.ndjson
  media_index.json
  progress_events.ndjson
  review_strings.txt
  dates/
    YYYY-MM-DD/
      post_<post_id>/
        post.md
        post.json
        static_screenshot.png
        media/images/
        media/videos/
        media/manifests/
        media/segments/
        replies/
      repost_<repost_id>__original_<original_post_id>/
        post.md
        post.json
        repost_context.json
        static_screenshot.png
        media/...
```

## Boundaries

- This is a local ledger/export-map layer, not a WebView2 runner.
- It can consume observations from R42GZ/R42GY/R42GV or future account timeline runners.
- It copies only local screenshot/media files already available.
- Remote candidates are preserved as `.url.txt` receipts.
- It performs no remote media download, no hidden X API scraping, no cookie/token extraction, no challenge bypass, no source-role checks, no source-role assignment, and no review-window rewrite.

## Date policy

Primary date folder = visible post date.
Fallback date folder = capture date.
Unknown = `dates/unknown_date/`.

## Next

R43B should add the account timeline runner with progress, pause/recovery, and post/repost record feeding into this ledger.
