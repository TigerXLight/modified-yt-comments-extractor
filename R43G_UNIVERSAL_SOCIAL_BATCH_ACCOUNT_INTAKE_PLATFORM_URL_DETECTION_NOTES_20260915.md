# R43G — Universal Social Batch Account Intake And Platform URL Detection

Marker: `YTCE_R43G_UNIVERSAL_SOCIAL_BATCH_ACCOUNT_INTAKE_PLATFORM_URL_DETECTION`

Status target: `PASS_R43G_UNIVERSAL_SOCIAL_BATCH_ACCOUNT_INTAKE_PLATFORM_URL_DETECTION`

## Scope

R43G adds a platform-neutral batch intake layer above R43F.

It accepts one URL, many URLs, pasted mixed text, or a TXT file and detects account/post URLs for:

- Twitter/X
- Bluesky
- Instagram
- Facebook
- Threads
- Mastodon/Fediverse baseline
- TikTok
- Reddit
- YouTube
- news comments
- unknown/unsupported URLs

Every item routes through R43F first, then R43E adapter map, then the concrete platform adapter where implemented.

Twitter/X remains the first adapter implementation, not the architecture.

## Boundaries

- no WebView2/CefSharp session started by R43G
- browser engines remain observation feeds only
- no copied WebView2 internals
- no hidden API scraping
- no cookie/token extraction
- no CAPTCHA/challenge bypass
- no source-role checks
- no review-window dependency or rewrite
- no remote media downloads
- no YouTube capture-engine change