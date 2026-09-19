# R45D Facebook auto-expand comments runner

R45D adds the live layer that R45C exposed as missing in the first real Facebook run.

The observed R45C live capture reached the correct post/context and matched the key sentinels, but it only captured a small loaded subset of the reference dump:

- `comment_count=22`
- `candidate_filtered_line_count=66`
- `reference_filtered_line_count=2482`
- `coverage_ratio=0.02054794520547945`
- sentinel phrases matched, so context was correct, but most comments were not loaded/expanded.

R45D therefore adds a visible-page auto-expand loop:

1. Launch or attach to the operator-controlled signed-in Facebook Chromium/WebView2 session.
2. Sanitize accidental Markdown-style URL pastes such as `[url](url\&id=...)` back to a raw URL.
3. Inject CSS-only comments focus mode. This hides page chrome but does not delete comment DOM.
4. Click only visible expansion controls matching labels such as `View more comments`, `View replies`, `View more replies`, `See more`.
5. Scroll the visible page between rounds.
6. Capture raw DOM, visible `innerText`, full screenshot, and optional tile screenshots.
7. Compare loaded text to the Print Edit WE reference dump.

Safety boundaries remain unchanged:

- no hidden Facebook API scraping
- no cookie/token extraction
- no browser profile copying/parsing
- no login automation
- no remote media downloads
- visible page clicks only, using the signed-in browser session controlled by the operator

If comparison coverage remains low, R45D reports `NEEDS_MORE_EXPANSION_R45D_FACEBOOK_AUTO_EXPAND_COMMENTS_RUNNER` rather than pretending the capture is complete.
