# Manual Archive URL Metadata

Date: 2026-07-10

## Purpose

`total_export_manual_archive.py` defines a local-only metadata skeleton for archive URLs that a user manually supplies for a source.

It is an Archive Phase 0 / Phase 1 foundation from `SOURCE_PRESERVATION_ROADMAP.md`. It stores and reports local notes only. It does not check archive services, submit URLs, fetch pages, scrape, download media, run browser automation, store credentials, or wire anything into the GUI.

## Fields

- `source_url`: Original source URL as supplied by the user or local workflow.
- `normalized_url`: Pure-local normalized source URL when available. YouTube URLs use the existing local YouTube URL helper.
- `archive_url`: Archive URL manually supplied by the user.
- `archive_service_name`: Locally detected service label, such as `internet_archive`, `archive_today`, or `unknown`.
- `archive_capture_time`: Optional user-entered archive capture timestamp or label.
- `archive_status`: User-entered local status.
- `archive_notes`: User-entered notes.
- `entered_at_utc`: Local entry timestamp.
- `verified_by_user_at_utc`: Optional timestamp for user verification.

## Status Meanings

Statuses are local/user-entered notes only. They are not proof from archive services.

- `not_checked`: No archive status has been checked or supplied.
- `manually_supplied`: The user supplied an archive URL.
- `manually_checked_found`: The user says they manually checked and found an archive.
- `manually_checked_not_found`: The user says they manually checked and did not find an archive.
- `manual_follow_up_needed`: More manual review is needed.
- `not_applicable`: Archive metadata is not applicable for this source.

## Service Detection

Service detection is string-only and local:

- `archive.org` and `web.archive.org` map to `internet_archive`.
- `archive.ph`, `archive.today`, `archive.is`, and `archive.vn` map to `archive_today`.
- Other URLs map to `unknown`.

The helper does not fetch, verify, validate, or submit archive URLs.

## Safety Notes

- Archive URL presence does not prove the archive URL is correct unless the user verifies it.
- Missing archive metadata is unknown, not proof that no archive exists.
- A `manually_checked_not_found` status records only the user's local note.
- Do not store secrets, credentials, private cookies, screenshots, downloaded media, or transcripts in this metadata.
- Future CLI/report integration should be a separate approved milestone and must remain local-only unless explicit network/archive behavior is approved later.
