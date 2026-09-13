# R42GP YouTube Searchable HTML + Optional Profile URL Export Surface

Marker: `YTCE_R42GP_YOUTUBE_SEARCHABLE_HTML_PROFILE_URL_EXPORT_SURFACE`

Target status: `PASS_R42GP_YOUTUBE_SEARCHABLE_HTML_PROFILE_URL_EXPORT_SURFACE`

## Scope

R42GP is an offline output/export-surface pass. It adds a standalone YouTube searchable HTML and optional author/channel profile URL sidecar generator for already-captured or preserved YouTube comment records.

It does not run YouTube capture, browser automation, screenshot capture, yt-dlp, JDownloader, network fetches, credential/token access, CAPTCHA/security bypass, source-role assignment, review-window rewrites, counter/no-jump mutation, or metadata promotion.

## Existing Protected Output

The existing YouTube readable TXT/Notepad-friendly route remains protected. R42GP writes a sibling TXT reference through the existing `evidence_exporter._write_readable_txt` format and does not replace the existing indentation/thread/reply-level output.

## Added Export Surfaces

- `profile_media_youtube_searchable_html_profile_export_r42gp.py`
  - renders a local self-contained searchable HTML comments file from supplied comment records;
  - preserves visible parent/reply nesting, depth, thread context, IDs, author, timestamp, likes, and text;
  - includes local search, result copy, and TXT download controls;
  - creates optional profile/channel URL sidecar JSON/CSV/HTML only when `include_author_profile_urls=True`;
  - keeps `include_author_profile_urls` disabled by default;
  - keeps machine URL fields plain and not Markdown-wrapped.

- `profile_media_youtube_searchable_html_profile_export_r42gp_test.py`
  - verifies static/local generation;
  - verifies no remote script/style URLs;
  - verifies parent/reply nesting;
  - verifies existing readable TXT output remains a separate sibling artifact;
  - verifies profile sidecars are optional;
  - verifies generated report JSON reloads with plain URL fields;
  - verifies R42GO remains compatible.

## MSN Comparison Policy

MSN V34 and V35 remain presentation/ergonomics references only:

- V34: local searchable HTML and copy/download search-results ergonomics.
- V35: profile URL/account sidecar ergonomics.

R42GP does not convert YouTube output to MSN format and does not replace YouTube's existing readable indentation/thread/reply export.

## Report Outputs

The CLI writes:

- `R42GP_YOUTUBE_EXPORT_SURFACE_MANIFEST.json`
- `R42GP_YOUTUBE_SEARCHABLE_HTML_PROFILE_EXPORT_REPORT.json`
- `R42GP_YOUTUBE_SEARCHABLE_HTML_PROFILE_EXPORT_REPORT.md`
- `youtube-comments-searchable-r42gp.html`
- `comments_readable_existing_format_reference.txt`
- `youtube-author-profile-sidecar.json`
- `youtube-author-profile-sidecar.csv`
- `youtube-author-profile-sidecar.html`
- `with_profile_urls_enabled_sample/` opt-in sample outputs

All URL-like machine fields are plain strings, not Markdown links.
