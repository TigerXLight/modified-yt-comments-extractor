# R45AM visible text count + autostart runner

R45AM keeps the stable legacy/fail-fast engine and adds a separate visible text-node counter.

Why:
- R45AL's role/button preflight could report zero even when visible labels such as
  "View all 34 replies", "View hidden replies", "View more replies", and
  "Name replied · N replies" were visible in the Facebook comments surface.
- The user no longer wants the `--pre-expand-pause` start gate when already signed in.

What it adds:
- `R45AM_PRE_EXPAND_VISIBLE_TEXT_CONTROL_COUNT`
- `R45AM_POST_EXPAND_VISIBLE_TEXT_CONTROL_COUNT`
- `R45AM_VISIBLE_TEXT_MISSED_REPORT`

Categories counted:
- `view_all_replies`
- `view_hidden`
- `view_more_replies`
- `view_number_replies`
- `replied_buckets`

Use it without `--pre-expand-pause` for autostart.

Safety:
- visible page only
- no hidden Facebook APIs
- no cookies/tokens/profile parsing
- no WebView2 storage inspection
- no login automation
