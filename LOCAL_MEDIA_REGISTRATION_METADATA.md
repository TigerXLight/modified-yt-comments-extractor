# Local Media Registration Metadata

Date: 2026-07-10

## Purpose

`total_export_local_media.py` defines a local-only metadata skeleton for media files that the user already has on disk.

It is a Phase 1 foundation from `SOURCE_PRESERVATION_ROADMAP.md`: local media import/register only. It stores and reports local filesystem metadata and user notes. It does not download media, fetch sources, call APIs, check archives, scrape, capture screenshots, probe media duration, transcribe, store credentials, or wire anything into the GUI.

## Fields

- `source_url`: Original source URL as supplied by the user or local workflow.
- `normalized_url`: Pure-local normalized source URL when available. YouTube URLs use the existing local YouTube URL helper.
- `package_id`: Optional Total Export package ID or local grouping label.
- `local_media_path`: User-supplied local file path.
- `local_media_filename`: Filename derived from the local path unless supplied.
- `local_file_size_bytes`: Local file size when present.
- `local_file_sha256`: Optional SHA-256 of the local file when explicitly computed.
- `media_type`: Extension/string-only label such as `video`, `audio`, `image`, or `unknown`.
- `duration_seconds`: Optional user-entered/manual duration; no media probing is performed.
- `media_notes`: User-entered notes.
- `registered_at_utc`: Local registration timestamp.
- `verified_at_utc`: Optional local/user verification timestamp.
- `exists_at_registration`: Whether the local file existed when the record was built.
- `hash_algorithm`: Hash algorithm label, currently `sha256`.
- `status`: Local/user-entered status.

## Status Meanings

Statuses are local filesystem/user-entered notes only. They are not proof that a remote source is available or unavailable.

- `registered`: A local file existed when the record was built.
- `missing_local_file`: The local file path did not exist when the record was built.
- `hash_mismatch`: Reserved for future local verification workflows.
- `needs_review`: More manual review is needed.
- `not_applicable`: Local media metadata is not applicable for this source.

## Media Type Detection

Media type detection is extension/string-only:

- `.mp4`, `.mkv`, `.webm`, `.mov`, `.avi`, `.m4v` map to `video`.
- `.mp3`, `.wav`, `.m4a`, `.flac`, `.ogg`, `.aac` map to `audio`.
- `.png`, `.jpg`, `.jpeg`, `.webp`, `.gif`, `.bmp` map to `image`.
- Other extensions map to `unknown`.

The helper does not inspect codecs, streams, duration, thumbnails, EXIF data, or media content.

## Safety Notes

- Local file presence and hashes describe only local filesystem state at registration/check time.
- Missing local files are local notes, not proof that a remote source is unavailable.
- This metadata must not include secrets, credentials, private cookies, downloaded media created by this app, transcripts, screenshots, or archive-service results.
- Future CLI/report integration should be a separate approved milestone and must remain local-only unless explicit network/download/archive behavior is approved later.
