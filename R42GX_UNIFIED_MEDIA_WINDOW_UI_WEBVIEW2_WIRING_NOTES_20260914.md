# R42GX — Unified Media Window UI + Background WebView2 Wiring

Marker: `YTCE_R42GX_UNIFIED_MEDIA_WINDOW_UI_WEBVIEW2_WIRING`

Status target: `PASS_R42GX_UNIFIED_MEDIA_WINDOW_UI_WEBVIEW2_WIRING`

This patch wires the R42GW unified media model into the app UI path for X/Twitter source rows.

## Intended UI model

- One Media window.
- Tabs: `All`, `Images`, `Videos`.
- Review window remains separate.
- All tab uses a JDownloader-style package/folder tree.
- Images/Videos tabs are filtered projections of the same model.
- Segmented media is listed as children under the video/manifest package.
- Segment children are not selected by default unless a site-specific/file policy permits it.

## Background WebView2 policy

Background WebView2 is recorded as the fast per-link observer policy for media-window population. Visible WebView2/Edge remains the escalation route for login, challenge, consent, access-control, or human visual confirmation.

## Boundaries

- No hidden X API scraping.
- No login automation.
- No token/cookie extraction.
- No CAPTCHA/challenge bypass.
- No paywall/access-control bypass.
- No download action in this patch.
- No source-role assignment.
- No review-window rewrite.
- No YouTube capture-engine change.

## JDownloader source usage

JDownloader source/framework/logic/code adaptation is allowed when attributed, provenance-bounded, and licence-compatible. This patch keeps that policy explicit and does not weaken it into a blanket “no code copy” rule.
