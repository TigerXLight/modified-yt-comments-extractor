# R42GG Universal Source Map Reconciliation Notes

Status target: `PASS_R42GG_UNIVERSAL_SOURCE_MAP_RECONCILIATION`

This pass adds a first-class universal source-map and method registry layer without replacing the existing source-role, review-window, source-row, counter, no-jump, or archive-inheritance paths.

## Implemented

- Universal source family map covering social/comment, video/media, live chat, creator-owned video hubs, short-form apps, microblogging, image/photo, forums/Q&A/link aggregators, news/comment systems, professional platforms, workplace/chat, podcast/audio, archive preservation, generic web/article/media, and local/imported evidence.
- Per-family method dimensions for metadata, text, comments/replies, live chat, media discovery/materialization, rendered capture, archive, RSS/enclosure, API3128/JDownloader, yt-dlp, WebView2/visible browser, local import, manual receipt import, human-chain, rate-limit recovery, and prohibited/no-bypass states.
- URL/TXT sanitizer for markdown wrappers, bare URLs, escaped underscores/backslashes, trailing punctuation, tracking query cleanup, and `twitter.com` to `x.com` normalization.
- Podcast handling that keeps Apple/Spotify podcast episodes public-download-capable when RSS enclosure, yt-dlp, browser-backed source evidence, or local receipt import works.
- Spotify music/DRM stays unsupported/prohibited.
- X/Twitter method slots for gradual discovery, local/export/manual receipt import, media discovery/materialization when a backend or browser session exposes downloadable media, human-chain, and dynamic rate-limit pause/recovery.
- Observed X benchmark for `https://x.com/examaddaorg` recorded as dynamic behavior evidence, not as a hard-coded limit.
- Canonical evidence record, single-post markdown card rendering, account/timeline export layout, and review-string bridge.
- CLI/report marker: `YTCE_R42GG_UNIVERSAL_SOURCE_MAP_RECONCILIATION`.

## Guardrails

- No network fetch.
- No live browser launch.
- No media download.
- No extension execution.
- No CAPTCHA/security bypass.
- No credential/cookie/token harvesting.
- No source-role/counter/no-jump mutation.

## Compatibility

R42GG imports and leaves intact the existing R42GC/R42GD/R42GE/R42GF families and source-adapter modules. Evidence records are converted to review strings so existing review-window/source-role matching can consume the output without a new incompatible review system.

## Verification Environment Note

The `py -3.11` launcher on this Codex shell resolves to a WindowsApps stub that returns `Access is denied`. Validation was run with the installed Python 3.11 executable at `C:\Users\fahad\AppData\Local\Programs\Python\Python311\python.exe`, using the same module/test list from the handoff.
