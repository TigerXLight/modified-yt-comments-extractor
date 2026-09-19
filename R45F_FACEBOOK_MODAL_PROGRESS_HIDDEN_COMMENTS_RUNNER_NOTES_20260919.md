# R45F Facebook modal progress + hidden-comments runner

R45F extends the Facebook live capture lane after the R45E live observation that the page was inside a Facebook post modal showing `438 of 715`, with remaining controls such as `View hidden comments` and `View 1 reply`.

R45F adds:

- modal/dialog scroller preference;
- visible progress parsing such as `438 of 715`;
- visible `View hidden comments` clicking;
- `View 1 reply` / `View all replies` / `View more replies` support;
- modal/container wheel-style scroll loading before and after clicks;
- low-coverage results remain `NEEDS_MORE_EXPANSION`, not success.

Safety remains unchanged: no hidden Facebook APIs, no Graph endpoints, no cookies/tokens, no browser profile file parsing/copying, no login automation, no remote media downloads.
