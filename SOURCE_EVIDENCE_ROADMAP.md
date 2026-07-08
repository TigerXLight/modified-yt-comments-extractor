# Source Evidence Roadmap

This is planning only. The local `reference_feature_notes/` files are private reference material and must stay ignored. Do not copy raw source code or large text from those notes into the repo.

## Track A: Source / Comment Adapters

- YouTube remains the only currently implemented adapter.
- Preserve existing YouTube comments/livechat behavior while adding future source support.
- Future platforms to consider:
  - Reddit.
  - TikTok.
  - Twitch live chat.
  - Bluesky.
  - Threads.
  - Twitter/X.
  - Instagram.
  - Facebook.
  - Pinterest.
  - Medium.
  - Tumblr.
  - LinkedIn.
  - Quora.
  - News websites such as Telegraph/MSN-style pages.
  - Forums.
  - Other video/social platforms.
- Each platform needs site-specific rules, auth/API/browser strategy, and visible limitations.
- Do not assume one generic scraper can capture every comments section.
- Comments should preserve when the comment was posted when the platform provides it.
- Small reference IDs and permalinks should be included in exports where possible so evidence is traceable.

## Track B: Web Evidence Capture

- Capture screenshot.
- Capture full-page screenshot.
- Extract visible page text.
- Extract readable/article text where possible.
- Save HTML/source snapshot where allowed.
- Save metadata.
- Save source URL/canonical URL.
- Let user choose save folder.
- Save screenshot and extracted text paths in evidence metadata.
- Keep capture user-triggered, not automatic background scraping.
- User options should make capture scope clear before anything is saved.

## Track C: Archive / Check Backup

- Check existing Wayback Machine captures.
- Report latest available capture date/status where possible.
- Optionally submit URL to archive services later.
- Save archive URL/result in evidence export.
- Treat archive checking/submission as opt-in.
- Do not treat archive failure as proof content did not exist.
- Treat archive.ph/archive.today-style services as optional and separate from Wayback because behavior may differ.

## Track D: Optional Media-Download Inspiration

- Use Video DownloadHelper/JDownloader-style tools only as feature inspiration.
- Potential future ideas:
  - Detect media assets.
  - Show available media streams/options.
  - Let user choose download folder.
  - Save source URL and metadata.
  - Create an evidence manifest for downloaded media.
- Do not implement downloading now.
- Do not bypass DRM, paywalls, login restrictions, or site protections.
- Keep legal, ToS, and copyright risk visible to the user.

## Capture Options To Plan

- Posts.
- Comments.
- Replies.
- Live chat.
- Captions/transcripts.
- Screenshot.
- Full-page screenshot.
- Extracted text.
- HTML snapshot.
- Archive check.
- Archive submit.
- Media detection/download, future only.

## Provenance / Evidence Fields To Plan

- `source_url`.
- `canonical_url`.
- `archive_url` if available.
- `source_platform`.
- `adapter_name`.
- `capture_time_utc`.
- `item_id`, `comment_id`, or `post_id` where available.
- `parent_id` for replies.
- Author/display name.
- Author profile/channel ID where available.
- Comment/post timestamp.
- Like/reaction count where available.
- Reply count where available.
- Permalink.
- Fetch method: API/browser/manual/import.
- Raw JSON/HTML sidecar where available.
- Screenshot path where captured.
- Extracted text path where captured.
- Local file hash/checksum where useful.
- Capture/session ID or reference code so exported evidence can be traced.

## ASR Note

- There is no known truly infinite free hosted ASR API.
- Local/offline ASR remains the only practical unlimited option.
- Cloud ASR remains optional and quota/cost/API-key dependent.
