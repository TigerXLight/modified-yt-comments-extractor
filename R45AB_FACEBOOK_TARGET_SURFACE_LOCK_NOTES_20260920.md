# R45AB Facebook target-surface lock

Fixes the live failure where expansion began in the target comments modal, then lost the modal/comments surface and continued scrolling the outer facebook.com feed.

Rules:
- Expansion probing is locked to the visible Facebook comments dialog.
- Downward scrolling is locked to the dialog's own scrollable comments surface.
- The runner never calls window.scrollBy() during the expansion pass.
- If the comments dialog disappears, the runner stops and logs `R45AB_TARGET_SURFACE_MISSING_STOP` instead of expanding/scanning the feed.
- Markdown-wrapped target URLs are sanitized into a raw URL where possible.

Safety remains unchanged: visible-page clicks only; no hidden Facebook APIs, tokens, cookies, profile parsing, WebView2 storage inspection, or login automation.

## R45AB marker gatefix

The R45AB surface-locked probe now keeps the legacy `R45X_EXPAND_ONLY_PROBE` marker while also exposing `surface_marker: R45AB_SURFACE_LOCKED_PROBE`. This preserves existing R45X self-test gates and keeps the new dialog-surface lock visible for debugging.

## Marker gatefix v2

The R45AB source keeps the legacy `R45X_EXPAND_ONLY_PROBE` marker inside
`JS_FIND_FIRST_VISIBLE_EXPAND_CONTROL_R45V` as a compatibility marker for older
static tests. The active behavior remains R45AB target-surface locking: after a
large opener such as `View all 302 replies`, downward expansion remains inside
the Facebook post/comment surface instead of drifting to the feed/page body.

