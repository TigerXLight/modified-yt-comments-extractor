# R43C Visual Screenshot Receipt Materialization Gate

Marker: `YTCE_R43C_VISUAL_SCREENSHOT_RECEIPT_MATERIALIZATION_GATE`

Status target: `PASS_R43C_VISUAL_SCREENSHOT_RECEIPT_MATERIALIZATION_GATE`

R43C adds the screenshot receipt gate requested after the Edge R18 visual handover.

## Purpose

- Treat screenshot files as insufficient unless a receipt records visual materialization status.
- Add `static_screenshot_receipt.json` and `static_screenshot_receipt.md` beside each post/repost `post.md`.
- Add `screenshot_receipts_index.json` and a `## Screenshot receipts` section to `account_record.md`.
- Record `PASS`, `NEEDS_VISIBLE_HUMAN_CHECK`, or `MISSING` for each screenshot.
- Preserve the R18 rule: do not accept R17 DOM-only false-clean for screenshot evidence.

## Edge R18 baseline

R18 is the screenshot-safe Edge baseline. The hard YouTube visual gate is:

- `materialization_clean=true`
- `rendered_reply_openers=0`
- `rendered_read-more=0`
- `capture_gate=true`
- physical materialization/viewport receipt present

Twitter/X uses the same principle at card level: a post/repost screenshot needs card/viewport materialization receipt to be `PASS`; otherwise the screenshot exists but is `NEEDS_VISIBLE_HUMAN_CHECK`.

## Boundaries

- Local receipt annotation only.
- No WebView2 session started by R43C.
- No source-role checks.
- No review-window back-and-forth.
- No hidden X API scraping.
- No cookie/token extraction.
- No CAPTCHA/challenge bypass.
- No remote media download.
- No YouTube capture-engine change.
