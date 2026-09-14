# R42GS — YouTube Comment Sort + Spam Review Defaults / Full Capture Settings

## Scope

R42GS records and exposes YouTube comment sort/spam-review defaults without changing the proven capture route.

## Implemented

- Added `profile_media_youtube_comment_sort_spam_review_r42gs.py`.
- Added focused offline tests in `profile_media_youtube_comment_sort_spam_review_r42gs_test.py`.
- Preserved the current/default sort as `newest`, matching the existing `Date (Newest)` application default.
- Registered supported sort policy values:
  - `newest` -> existing YouTube API `order=time`
  - `oldest` -> existing YouTube API `order=time` plus local ascending sort
  - `top` -> existing relevance/likes path
- Made the default spam policy explicit as `review`.
- Switched new-session spam review default to separate suspected spam for review.
- Preserved existing spam review artifacts:
  - `spam_comments.csv` when flagged rows exist
  - readable TXT `FLAGGED SPAM` section where the existing extractor writer is used
- Added source-info settings keys for evidence packages:
  - `youtube_comment_sort_order`
  - `youtube_comment_sort_display`
  - `youtube_comment_sort_api_order`
  - `youtube_comment_sort_safe_engine_parameter`
  - `youtube_spam_handling`
  - `youtube_spam_handling_display`
  - `youtube_spam_review_default`
  - `default_preserves_existing_sort`
  - `newest_sort_supported_or_blocked`
  - `no_capture_executed_by_r42gs`

## Boundaries

R42GS is offline settings/audit/app plumbing only. It does not run live YouTube capture, comment scraping, browser/WebView2/CDP, screenshots, network fetches, yt-dlp, JDownloader, source-role assignment, review-window rewrites, counter/no-jump mutation, or metadata promotion.

## Verification marker

`YTCE_R42GS_YOUTUBE_COMMENT_SORT_SPAM_REVIEW_DEFAULTS`

## Pass status

`PASS_R42GS_YOUTUBE_COMMENT_SORT_SPAM_REVIEW_DEFAULTS`
