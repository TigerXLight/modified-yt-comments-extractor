# R42GZ Independent Fast Media WebView2 Capture Lane

- marker: `YTCE_R42GZ_INDEPENDENT_FAST_MEDIA_WEBVIEW2_CAPTURE_LANE`
- status target: `PASS_R42GZ_INDEPENDENT_FAST_MEDIA_WEBVIEW2_CAPTURE_LANE`
- baseline: `daf819a Add background WebView2 media observer runtime`

## What changed

R42GZ registers a separate, per-link Media-window capture lane for the R42GY background observer. This lane is deliberately independent from the slower review/source-role WebView2 path.

The lane is:

- media-only
- per-link
- independent from the review window
- independent from source-role UI loops/checks
- backed by its own profile/user-data setting
- backed by its own output/state folder
- connected into the existing R42GY -> R42GV -> R42GW -> R42GX media pipeline

R42GZ can reuse safe lower-level browser-capture primitives where available, but the app contract forbids routing this Media-window fast path through the review/source-role WebView2 lane or its back-and-forth source-role material judgement loop.

## Boundaries

R42GZ does not download remote media, assign source roles, rewrite the review window, automate login, extract cookies/tokens, bypass CAPTCHA/challenges, bypass paywalls/access controls, perform hidden X API scraping, or change the YouTube capture engine.

Visible WebView2/Edge remains the human-confirmation escalation path for login/account chooser, consent, CAPTCHA/challenge, access barriers, visual confirmation, or insufficient rendered/session material.

## Source usage policy

JDownloader source/framework/logic/direct code adaptation remains allowed when attribution, provenance, and licence compatibility are recorded. R42GZ does not include direct JDownloader source.
