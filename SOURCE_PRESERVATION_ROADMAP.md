# Source Preservation Roadmap

Date: 2026-07-10

## Scope

This is a local-only planning document for future Total Export/source-evidence preservation work.

It does not implement behavior. It does not add downloads, archive service checks, archive submission, media capture, screenshots, browser automation, scraping, network calls, provider/API calls, credential storage, ZIP extraction, or GUI wiring.

The purpose is to preserve phase boundaries for later work so future source preservation features stay explicit, testable, and opt-in.

## Current Implemented Baseline

The current repo already has local-only Total Export foundations:

- Manifest and asset structures for package metadata.
- Explicit package-shell preparation from source plans.
- Review files such as README, summary, source-plan report, and inventory report.
- Local package inspection and validation.
- Deterministic local ZIP packaging for already-prepared package folders.
- ZIP inspection and sidecar writing for local ZIP files.
- Review-bundle build and verification helpers.
- Folder-level review-bundle verification without ZIP extraction.
- Batch review-bundle planning, building, and reconciliation from local UTF-8 source lists.

These helpers do not fetch source content, download media, submit to archives, inspect external services, scrape pages, launch browsers, call ASR providers, or wire into the GUI.

ASR comparison tooling is separate and also local-only: it records/renders manually entered results and does not call providers or run transcription.

## Hard Boundaries

Do not implement or add these behaviors in this roadmap phase:

- Media downloading.
- YouTube downloading.
- Source fetching.
- Comment or live chat fetching.
- YouTube API calls.
- Archive.ph/archive.today checks.
- Internet Archive checks.
- Archive submission.
- External archive status checking.
- Screenshots.
- Browser automation.
- Scraping.
- ASR provider calls.
- Transcription.
- API/network calls.
- Credential storage.
- ZIP extraction.
- GUI wiring.
- Runtime dependencies.
- Hidden configuration.
- Login, paywall, private-content, or DRM bypass logic.

Any future behavior change must be explicit, separately approved, and covered by local or mocked tests before it is trusted.

## Phase 0: Documentation-Only Roadmap

This file is Phase 0.

The goal is to define what may be considered later and what is explicitly out of scope now. No code, CLI mode, GUI behavior, capture logic, archive behavior, downloader behavior, or network behavior is added in this phase.

## Phase 1: Local Media Import/Register Only

Future work may add local media registration for files the user already has on disk.

Allowed future behavior:

- Accept a user-supplied local media path.
- Record filename, local path, size, hash/checksum, and media type when locally available.
- Record optional user notes about source relationship.
- Link the local media record to a Total Export package/source URL/provenance record.
- Validate local existence and hash consistency.

Out of scope for Phase 1:

- Downloading media.
- Fetching source pages.
- Capturing media streams.
- Calling video/social APIs.
- Browser automation.
- Scraping.
- DRM, paywall, login, private-content, or anti-copy bypass.

Possible future metadata fields:

- `local_media_path`
- `local_media_filename`
- `local_file_hash`
- `local_file_size_bytes`
- `media_type`
- `duration_seconds`
- `source_url`
- `normalized_url`
- `package_id`
- `user_notes`
- `registered_at_utc`
- `verified_at_utc`

## Phase 2: Preservation/Capture Plan Report Only

Future work may add a local preservation plan report that identifies what is missing and what the user may want to preserve manually.

Allowed future behavior:

- Report sources that have no registered local media.
- Report sources that have no manually supplied archive URL.
- Report package/source records that lack hashes, notes, or verification timestamps.
- Recommend user actions such as manually saving a file, manually adding an archive URL, or manually importing a screenshot path.

Out of scope for Phase 2:

- Downloading media.
- Capturing screenshots.
- Checking archive services.
- Submitting URLs to archive services.
- Fetching web pages.
- Scraping.
- Browser automation.
- API/network calls.

The report should be a local plan only, not proof that content exists or does not exist elsewhere.

## Phase 3: Adapter Design Only

Much later, and only after explicit approval, the project may design optional adapter interfaces for media/download/archive tooling.

Allowed future design-only topics:

- Adapter capability declarations.
- Required user prompts/confirmations.
- Local/mock test surfaces.
- Privacy/cost/rate-limit warnings.
- Per-source limitations and unsupported cases.
- Failure reporting without treating absence as proof.

Out of scope for Phase 3:

- Implementing downloaders.
- Implementing archive checks or submits.
- Implementing browser automation or scraping.
- Calling external services.
- Adding credentials.
- Making adapters default-on.

Adapters should remain disabled by default until a later explicit implementation milestone.

## Manual Archive URL Phases

### Archive Phase 0: User-Supplied Archive URL Fields

Future metadata may record archive URLs that the user supplies manually.

Possible fields:

- `source_url`
- `normalized_url`
- `user_supplied_archive_url`
- `archive_service_name`
- `archive_capture_time`
- `archive_notes`
- `entered_at_utc`
- `verified_by_user_at_utc`

This phase must not check archive services or submit URLs.

### Archive Phase 1: Archive Plan Report

Future local reports may show which sources do or do not have manually supplied archive URLs.

The report may recommend manual follow-up, but it must not call archive services or infer that missing archive metadata proves a page was never archived.

### Archive Phase 2: Local Archive Status Registry

Future work may maintain local user-entered archive statuses, such as:

- `not_checked`
- `manually_supplied`
- `manually_checked_found`
- `manually_checked_not_found`
- `manual_follow_up_needed`
- `not_applicable`

These statuses are local notes only. They are not external verification unless the user separately records evidence.

### Archive Phase 3: Optional Automated Archive Checks/Submits

Automated archive checks or submissions are not approved now.

They may be considered only much later, after explicit approval, with careful handling of privacy, rate limits, user confirmation, and service-specific behavior.

Archive submit/save must never happen silently.

## Safety And Legal/Ethical Boundaries

Future source preservation features must:

- Keep capture actions user-triggered and explicit.
- Avoid credential harvesting.
- Avoid storing secrets in packages, manifests, logs, screenshots, sidecars, reports, or exports.
- Avoid bypassing paywalls, login walls, private content controls, DRM, meters, anti-copy controls, or site protections.
- Avoid presenting local metadata as legal advice.
- Preserve source limitations and uncertainty in reports.
- Treat missing metadata as unknown, not proof that content does not exist.
- Keep cloud/network features opt-in where they are ever approved.

## Future Data Fields

Candidate fields for later metadata skeletons:

- `source_url`
- `normalized_url`
- `source_platform`
- `adapter_name`
- `package_id`
- `capture_session_id`
- `local_media_path`
- `local_media_filename`
- `local_file_hash`
- `local_file_size_bytes`
- `media_type`
- `duration_seconds`
- `user_supplied_archive_url`
- `archive_service_name`
- `user_entered_archive_status`
- `archive_notes`
- `source_relationship_notes`
- `created_at_utc`
- `registered_at_utc`
- `verified_at_utc`
- `updated_at_utc`

These fields are planning targets only until a later explicit implementation milestone.

## Candidate Future Milestones

Possible local-only next milestones:

1. Manual archive URL metadata skeleton.
   - Local fields only.
   - No archive service checks.
   - No archive submission.

2. Local media registration metadata skeleton.
   - User-supplied local file paths only.
   - Hash/size metadata.
   - No downloads or fetching.

3. Local preservation plan report.
   - Report missing local media registrations and missing manual archive URLs.
   - No external checks.

4. Local bundle index.
   - Index existing review-bundle ZIPs and sidecars.
   - No ZIP extraction.
   - No network behavior.

## Explicit Non-Goals For Now

This roadmap does not change runtime behavior.

It does not implement downloads, archive checks, archive submission, screenshots, scraping, browser automation, provider calls, source fetching, media capture, ZIP extraction, credential storage, or GUI wiring.
