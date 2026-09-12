# R42GE BBC Sounds + Podcast Episode Adapter

R42GE formalises public broadcast/podcast episode handling as a specialist source family rather than pretending it is a generic article or generic media page.

## Scope

- BBC Sounds / BBC programme URLs are recognised as `bbc_sounds`.
- The proven BBC recipe is preserved as a plan: `yt-dlp -f bestaudio` to an original full asset, then `ffmpeg -map 0:a:0 -c:a copy -map_metadata 0` to an M4A audio-only asset.
- Existing original assets are detected so large BBC programme files do not need to be re-downloaded.
- Apple Podcasts and public podcast RSS URLs are routed as public metadata/feed/enclosure candidates.
- Spotify is limited to podcast show/episode metadata handling. Spotify tracks, albums, playlists, and music downloads are explicitly out of scope.

## Safety and evidence boundary

The R42GE validator is side-effect-free:

- no network fetch
- no media download
- no screenshot
- no archive submission
- no provider/API call
- no account/session use
- no CAPTCHA, paywall, rate-limit, DRM, or access-control bypass

Transcripts, comments, screenshots, WARC/archive receipts, and source-role counter promotion remain receipt-gated until exercised by a later patch with actual evidence.
