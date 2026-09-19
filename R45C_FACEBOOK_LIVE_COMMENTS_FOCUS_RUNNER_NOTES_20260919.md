# R45C — Facebook live comments focus runner

R45C turns the R45B design into a live runner.

## Purpose

Use the same evidence pattern as the YouTube comment workflow:

1. Text-only extraction for searchable/exportable comments.
2. Screenshot/visual receipts for evidence.

For Facebook, the capture must be operator-controlled and visible. The tool must not use hidden Facebook APIs, automate login, or extract cookies/tokens.

## Method

Primary live method:

1. Open a logged-in Facebook post/permalink in Chromium or WebView2.
2. Apply comments-focus CSS only; do not delete DOM nodes before expansion.
3. The operator expands `View more comments`, `View replies`, and `See more` while buttons remain clickable.
4. Capture raw DOM, visible `innerText`, full-page screenshot, optional tiled screenshots.
5. Export comments to JSON, NDJSON, and Markdown.
6. If a Print Edit WE text dump such as `text.txt` is supplied, compare the captured text to it with filtered-line coverage and sentinel phrases.

## Safety contract

- No hidden Facebook API scraping.
- No login automation.
- No cookie/token extraction.
- No browser profile file reading, copying, or parsing.
- No WebView2 storage/cookie inspection.
- No remote media downloads.

## Notes

Text-only extraction can capture all comments only after Facebook has loaded/expanded them in the page DOM. Screenshots are not required for text extraction, but both lanes should be kept: screenshots for visual proof and JSON/Markdown/NDJSON for searching and analysis.
