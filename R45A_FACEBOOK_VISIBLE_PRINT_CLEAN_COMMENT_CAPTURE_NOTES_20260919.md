# R45A — Facebook visible print-clean comment capture adapter

## Status

`PASS_R45A_FACEBOOK_VISIBLE_PRINT_CLEAN_COMMENT_CAPTURE`

## Purpose

Start the Facebook source adapter layer after Reddit closeout.

The user has a logged-in Facebook account inside Chromium. The manual baseline is a Print Edit WE workflow where the user expands comments/replies first, then deletes/floats page chrome until comments are readable.

R45A records that workflow as a safe adapter contract and adds the first parser/extraction layer for print-clean Facebook comment text.

## Two-lane evidence method

This should mirror the established YouTube comments evidence pattern:

1. **Interactive visible lane** — keep Facebook live/clickable so the operator can expand comments/replies and capture screenshots.
2. **Static print-clean text lane** — after expansion, freeze/clean the DOM or text view and extract text.

The static print-clean surface is evidence, not an interactive browser page. After cleanup, clickability is not guaranteed and should not be required.

## Primary route

1. Use an operator-controlled signed-in Facebook Chromium/WebView2 session.
2. Open the Facebook permalink/post URL visibly.
3. Expand the required visible comments/replies before cleanup.
4. Capture screenshot/raw DOM while still interactive where required.
5. Apply Print-Edit-WE-like cleanup in code: remove scripts/styles/page chrome where possible.
6. Extract visible comment/reply text, displayed time/reaction text, and evidence outputs.

## Safety contract

- No login automation.
- No cookie/token extraction.
- No browser profile copying/parsing.
- No hidden Facebook API scraping.
- No WebView2 storage/cookie inspection.
- No remote media downloads.
- Only visible page content from the operator-controlled session is captured.

## Outputs

- `facebook_print_clean_comments.json`
- `facebook_print_clean_comments.ndjson`
- `facebook_print_clean_comments.md`
- `r45a_facebook_visible_print_clean_comment_capture_receipt.json`

## Next likely layer

R45B should be the live Chromium/WebView2 runner:

- direct-launch/attach to a logged-in Facebook permalink page;
- preserve an interactive pre-clean surface for expanding comments/replies;
- capture screenshots plus raw DOM;
- then run R45A print-clean text extraction;
- future R45C can handle comment-tree/reply indentation reconciliation.
