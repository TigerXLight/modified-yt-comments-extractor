# R42GI Universal Media Discovery Method Matrix Notes

Status target: `PASS_R42GI_UNIVERSAL_MEDIA_DISCOVERY_METHOD_MATRIX`

R42GI adds a static universal media discovery and materialization contract. It does not fetch the network, launch a browser, run yt-dlp, run JDownloader, execute extensions, bypass challenges, harvest credentials, mutate source roles, alter counters, or rewrite the review window.

## Implemented

- Media kind taxonomy covering images, video, audio, thumbnails, posters, avatars, banners, article media, post media, embedded players, RSS/podcast/catch-up audio, captions/transcripts, screenshots, snapshots, sidecars, and unknown binaries.
- Discovery method taxonomy covering DOM, OpenGraph, Twitter card, JSON-LD, RSS, browser/network observation, WebView2, API3128/JDownloader, yt-dlp Python module, extension/manual receipt, local import, archive replay, and screenshot capture.
- Media role taxonomy distinguishing primary post media, article body/header media, quoted/comment/reply media, avatar/banner, thumbnail/poster, embedded players, podcast/broadcast audio, screenshots, archive snapshots, sidecars, captions, manual receipts, and unknown media.
- Canonical `MediaCandidate` schema with plain machine URL/path fields and review strings.
- Canonical `MediaMaterializationPlan` schema with queue grouping, host grouping, priority, resume keys, sidecars, preservation policy, and side-effect boundary.
- Fast queue policy for text-first capture, immediate parent linking, dedupe, host grouping, pause/recovery, human-chain states, selected-media-only mode, and deferred low-priority materialization.
- Method slots for X/Twitter, generic article/news pages, public broadcast/catch-up audio, podcast audio, video platforms, visual/photo platforms, community/forums, and professional/workplace sources.
- Global Player/LBC fixture carried forward from R42GH with native M4A preservation and sidecars.
- Export layouts for universal media, public audio/catch-up, and generic articles.
- CLI/report marker `YTCE_R42GI_UNIVERSAL_MEDIA_DISCOVERY_METHOD_MATRIX`.

## Guardrails

- Metadata-only, review-required, blocked, private/protected, DRM, login-required, and prohibited candidates are not promoted to accepted evidence.
- Machine URL/path fields remain plain text, not markdown.
- Review strings bridge to existing source-role/review matching without changing that logic.

## Verification Environment Note

If `py -3.11` resolves to the WindowsApps stub and returns `Access is denied`, use `C:\Users\fahad\AppData\Local\Programs\Python\Python311\python.exe` and record that in verification output.
