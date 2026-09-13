# R42GO YouTube Proven Capability Registration / Source Row Boundary Audit

Marker: `YTCE_R42GO_YOUTUBE_PROVEN_CAPABILITY_REGISTRATION_SOURCE_ROW_BOUNDARY_AUDIT`

Status target: `PASS_R42GO_YOUTUBE_PROVEN_CAPABILITY_REGISTRATION_SOURCE_ROW_BOUNDARY_AUDIT`

## Scope

R42GO registers already-proven YouTube comment text/data capture and screenshot/visual capture capabilities into the current source-row, method-profile, evidence-bundle, and review-string vocabulary.

It does not execute YouTube capture, browser automation, screenshots, downloads, API calls, archive submission, JDownloader, yt-dlp, or extension workflows.

## Existing Live Repo Anchors

- `source_adapters.py` already exposes `YouTubeSourceAdapter` and `youtube_media_transcript_comment`.
- `source_resource_state.py` already exposes YouTube source rows, comment/livechat support, and separate screenshot intent flags.
- `capture_controller.py` already distinguishes `youtube_media_transcript` and `youtube_comments`.
- `profile_media_source_package_preview.py` already parses preserved YouTube comments, renders indented review text, and builds source-role records for preserved comments.
- `evidence_exporter.py` already writes readable YouTube comment packages and treats screenshots as attached evidence files.
- `source_msn_comments_profile_export.py` provides the MSN V34/V35 comparison pattern for searchable HTML and profile URL/profile sidecar exports.

## Registered YouTube Capabilities

- `comment_text_capture_proven`
- `comment_metadata_capture_proven`
- `reply_thread_level_indentation_format_proven`
- `screenshot_capture_proven`
- `visual_expansion_path_proven`
- `screenshot_tile_or_viewport_stitch_evidence_proven`
- `optional_author_profile_url_export`
- `searchable_html_export_capability`
- `no_engine_changes`

## Boundaries

- Text/data path remains independent from screenshot expansion.
- Visual/screenshot path remains independent from text export.
- Optional profile/channel URL export is registered as optional, not forced.
- MSN V34/V35 patterns are comparison references only and do not replace the YouTube output format.
- Source-role bridge is compatibility-only, not source-role assignment.
- Promotion status remains review bridge only.
