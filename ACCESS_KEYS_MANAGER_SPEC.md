# Access & Keys Manager Spec

Date: 2026-07-11

## Purpose

This document expands the roadmap-only `KEYS` / `Access & Keys` idea into a future UI, safety, and adapter-access specification.

It is planning only. It does not implement UI, credential storage, key testing, OAuth/login flows, browser profile access, provider calls, source fetching, archive checks, browser automation, scraping, media downloading, or Total Export wiring.

The goal is to replace the current one-off sidebar `API KEY` field with a scalable access manager that can support ASR providers, source adapters, archive services, browser-assisted capture settings, and manual/no-credential modes without implying that every source uses an API key.

## Naming

- Sidebar button: `KEYS`.
- Window title: `Access & Keys`.
- `KEYS` is shorter for the main UI.
- `Access & Keys` is more accurate for the window because access may involve API keys, OAuth-style login, app passwords, browser profile settings, manual import, or no credentials.

The main sidebar should stay focused on Source URLs, capture options, exports, and current workflow controls. Detailed access configuration belongs in the dedicated window.

## Current Baseline

Current behavior includes a sidebar `API KEY` field that primarily fits the YouTube Data API workflow.

Future source/provider coverage will not fit into one field because different adapters may need different access modes, privacy notes, cost/rate-limit warnings, setup steps, and connection-test behavior.

## Access Modes

Planned access modes:

- `NO_CREDENTIALS_REQUIRED`
- `API_KEY`
- `OAUTH_OR_BROWSER_LOGIN`
- `APP_PASSWORD`
- `USER_AUTHENTICATED_BROWSER_PROFILE`
- `DEDICATED_CAPTURE_BROWSER_PROFILE`
- `MANUAL_IMPORT_ONLY`
- `LOCAL_ONLY`
- `BLOCKED_OR_NOT_CONFIGURED`

Access mode should be reported per adapter/provider and, where relevant, per URL/session rather than globally for an entire platform.

## Credential Statuses

Planned credential/access statuses:

- `NOT_NEEDED`
- `OPTIONAL`
- `REQUIRED_MISSING`
- `CONFIGURED_UNTESTED`
- `CONFIGURED_TEST_PASSED`
- `CONFIGURED_TEST_FAILED`
- `EXPIRED_OR_REVOKED`
- `DISABLED_BY_USER`
- `UNSUPPORTED`

A status should distinguish missing credentials from unsupported functionality. Missing credentials should not be treated as proof that a source lacks content.

## Planned Window Layout

The future Access & Keys window may use searchable/filterable platform sections or tabs.

Suggested sections:

1. ASR providers.
2. Video and social video platforms.
3. Live streaming platforms.
4. Creator-owned and independent video hubs.
5. Short-form and entertainment mobile apps.
6. Text/microblogging platforms.
7. Image, photography, and visual platforms.
8. Community, forums, Q&A, and link aggregators.
9. News websites and site-family adapters.
10. Professional, jobs, experts, and portfolio platforms.
11. Workplace, chat, and collaboration platforms.
12. Archive services.
13. Browser-assisted capture.

The window should not list every possible service on the main screen at once. Use search, filters, collapsed groups, and adapter metadata so it remains manageable.

## ASR Provider Access

Future ASR provider entries may include:

- ElevenLabs.
- Groq.
- OpenAI.
- Deepgram.
- Speechmatics.
- Azure Speech.
- Google STT.
- AssemblyAI.
- AWS Transcribe if access becomes available.
- Other optional cloud ASR providers.

Local/offline ASR should remain available without cloud keys.

ASR provider access entries should show:

- Provider display name.
- Required credential type.
- Whether keyterms/custom vocabulary/phrase prompts are supported.
- Cost/rate-limit warning.
- Privacy warning.
- Current project status: candidate, rejected, blocked, external lead, or not tested.
- Whether connection testing is supported.
- Whether connection testing has been explicitly run by the user.

No provider test should run automatically in the background.

## Source Adapter Access

Future source adapter entries should show:

- Display name.
- Platform/source family.
- Current implementation state.
- Credential/access requirement.
- Supported capture types.
- Browser-assisted capture support.
- Manual import support.
- Access limitations.
- Setup hint.
- Privacy/cost/rate-limit notes.
- Whether connection testing is supported.

A source adapter may be public/no-credential, API-key based, OAuth/browser-login based, manual-import only, or not yet implemented.

## Archive Service Access

Archive services should distinguish read-only checks from submissions.

Planned archive service entries:

- Wayback Machine / archive.org check settings.
- Wayback save/submit settings.
- archive.ph / archive.today-style check settings.
- archive.ph / archive.today-style submit settings where appropriate.
- ArchiveBox-style local/self-hosted store settings.

Rules:

- Archive Check may later be default-on in Total Export if it is a read-only lookup and the user has approved that behavior.
- Archive Submit/Save must remain explicit and user-selected because it sends a URL to an external service.
- ArchiveBox-style local archiving must be explicit and user-triggered, with path/process boundaries clearly shown.
- Archive failure must not be treated as proof that content did not exist.

## Browser-Assisted Capture Settings

Future browser-assisted capture settings may include:

- Dedicated capture browser profile path.
- Browser family.
- User-authenticated capture notes.
- Access mode label.
- Capture method label.
- Profile safety warning.
- Whether the profile is dedicated to capture.
- Whether an existing profile was user-selected in an advanced mode.

Rules:

- Prefer a dedicated capture browser profile.
- Do not harvest passwords, cookies, private tokens, or hidden session credentials.
- Existing browser profile use should be advanced, user-approved, and technically safe before support is added.
- Browser-assisted capture should record access mode and capture method.
- Browser-assisted capture must not bypass DRM, paywalls, login restrictions, private access controls, meters, anti-copy controls, or site protections.

## Secret Safety Principles

The future manager must follow these principles:

- Mask secrets by default.
- Provide reveal/copy/clear controls only where appropriate.
- Do not write secrets into exports, logs, manifests, screenshots, extracted text, raw sidecars, evidence packages, Total Export folders, activity logs, crash logs, or debug reports.
- Never commit secrets.
- Prefer environment variables or local user settings initially.
- Consider OS keyring or encrypted local storage only in a later explicit milestone.
- Do not silently migrate secrets into a new storage backend.
- Do not test keys automatically.
- Do not send a key to a provider unless the user explicitly triggers a test or run that requires it.
- Do not show full secrets in command output.
- Do not include secrets in clipboard/export unless the user explicitly requests a reveal/copy action.

## Setup And Test Behavior

Testing an access entry should be explicit and user-triggered.

Planned test states:

- `TEST_NOT_SUPPORTED`
- `TEST_NOT_RUN`
- `TEST_RUNNING`
- `TEST_PASSED`
- `TEST_FAILED`
- `TEST_SKIPPED_BY_USER`

A test result should show:

- Provider/adapter name.
- Time tested.
- Test type.
- Success/failure state.
- Short safe diagnostic.
- Rate-limit/cost warning where relevant.

Diagnostics must not include secrets, cookies, raw authorization headers, or private tokens.

## Adapter/Provider Metadata Contract

Each future adapter/provider should eventually declare non-secret metadata such as:

- `display_name`
- `platform_family`
- `implementation_state`
- `credential_type`
- `credentials_required`
- `credentials_optional`
- `credential_status`
- `access_mode`
- `supports_browser_capture`
- `supports_manual_import`
- `supports_connection_test`
- `supports_comments`
- `supports_replies`
- `supports_live_chat`
- `supports_captions_or_transcripts`
- `supports_visible_text`
- `supports_article_text`
- `supports_screenshot`
- `supports_archive_check`
- `supports_archive_submit`
- `supports_media_evidence`
- `setup_hint`
- `privacy_notes`
- `cost_or_rate_limit_notes`
- `access_limitations`
- `last_tested_at_utc`
- `last_test_status`

This metadata should be safe to render in docs, reports, and UI because it does not contain secrets.

## Relationship To Evidence Item Queue

The evidence item queue should be able to show when an item cannot proceed because an adapter/provider has missing or disabled access.

Examples:

- A source URL item may show that comments require an adapter not implemented yet.
- A cloud ASR item may show that a provider key is missing.
- A browser-assisted capture item may show that a dedicated capture profile is not configured.
- An archive-submit action may show that submit/save is disabled until explicitly selected.

The queue should show access limitations without trying to fix them silently.

## Relationship To Total Export

Total Export may later use access metadata to record:

- Access mode.
- Capture method.
- Adapter/provider name.
- Credential status label, never the secret itself.
- Archive check/submit status.
- Browser-assisted capture profile label, never private session data.
- Manual import status.

Total Export should never include secrets or hidden session data.

## Migration From Current Sidebar API Key

A future migration should be explicit and safe.

Possible plan:

1. Keep the existing sidebar field working until the Access & Keys window exists.
2. Introduce `KEYS` button.
3. Show the current YouTube Data API key as a YouTube access entry if already configured.
4. Avoid silently duplicating or exposing the key.
5. Let the user clear or move the key only through explicit UI actions.
6. Eventually reduce or remove the old sidebar API-key field after the new window is stable.

## Explicit Non-Goals For This Spec

This spec does not add:

- Access & Keys window.
- Credential storage.
- Credential migration.
- Key testing.
- OAuth/login flows.
- Browser profile integration.
- Provider/API calls.
- Source fetching.
- Archive checks/submissions.
- Browser automation.
- Scraping.
- Media downloading.
- GUI wiring.
