# R45Y Facebook pre-pause target tab guard

Fixes the run opening/showing a restored generic `facebook.com` feed tab before the operator pause when a specific permalink was requested.

## Behaviour

- Opens a fresh Playwright page/tab for the requested target URL when `--target-url` is supplied.
- Uses `--disable-session-crashed-bubble` plus no-first-run/no-default-browser-check launch flags.
- Runs the target-page guard before `R45J_PRE_EXPAND_PAUSE`, so the operator should see the requested post/permalink, not the restored feed.
- Re-runs the target-page guard after the pause before expansion.
- Leaves old restored tabs alone but ignores them as the working page.
- Keeps R45X expand-comments-only behaviour unchanged.

## Safety

Visible page navigation and clicks only. No hidden Facebook APIs, no cookie/token extraction, no browser profile parsing/copying.
