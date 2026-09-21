# R45BA — Fix R45AX real comments scroller selection

R45AZ fixed Facebook CSP script installation, but the live run still falsely passed because R45AX selected the outer Facebook `role="dialog"` shell:

- `scrollHeight: 720`
- `clientHeight: 720`
- `atBottom: true`
- `clicked: 0`
- no detected progress text

That is not the scrollable comments container. R45BA changes the active scroller selection so the runner only accepts a real scrollable comments container where `scrollHeight > clientHeight + 80`. It also removes the previous role=dialog bonus that caused the outer shell to win over the inner comments scroller.

Expected behaviour now:

1. If the runner only sees the outer 720px dialog shell, it blocks with `BLOCKED_NO_REAL_SCROLLABLE_COMMENTS_SCROLLER` instead of falsely passing.
2. If the inner comments scroller is present, it is selected and logged in `R45AX_ACTIVE_SCROLL_CONTAINER` with a real `scrollHeight` larger than `clientHeight`.
3. The existing R45AX behaviour remains: visible-page-only clicking, progress gate such as `657 of 715`, modal flattening, and maximum-height comments-only screenshots.

Safety stays the same:

- no hidden Facebook APIs
- no cookies/tokens extraction
- no browser profile parsing/copying
- no WebView2 storage inspection
- no remote media downloads
