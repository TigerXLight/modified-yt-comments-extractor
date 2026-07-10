# Source Preservation Current State

Date: 2026-07-10

Checkpoint: `44f660a Add bundle index reconciliation CLI`

## Purpose

This document is the handoff/index for the current local-only source-preservation work. It maps the implemented metadata models, report helpers, CLIs, tests, and documentation so a future session can resume without reconstructing the full project history.

This is a state document, not an implementation. The preservation stack remains separate from the GUI and existing YouTube comment/live-chat, ASR, and Total Export runtime flows.

## Current Hard Boundaries

The current preservation helpers may read explicitly selected local metadata/files, calculate local hashes when requested, compare local paths, and render local reports. They do not:

- Extract ZIP files or read files inside ZIPs.
- Download media or source content.
- Fetch YouTube comments, replies, live chat, captions, or metadata.
- Call YouTube, archive, ASR, provider, HTTP, or other network APIs.
- Check or submit URLs to Internet Archive, archive.ph/archive.today, or another archive service.
- Scrape pages, automate browsers, or capture screenshots.
- Transcribe media or call ASR providers.
- Store credentials, secrets, cookies, or browser sessions.
- Bypass login, paywall, private-content, anti-copy, or DRM controls.
- Wire preservation behavior into the GUI.

Missing metadata, missing local files, and missing expected bundles are follow-up signals only. They are not proof that remote content was deleted, never existed, or is unavailable.

## Helper And Documentation Index

| Area | Documentation | Helper/CLI files | Tests | Purpose | Local-only boundary |
| --- | --- | --- | --- | --- | --- |
| Manual archive URL metadata | `MANUAL_ARCHIVE_URL_METADATA.md` | `total_export_manual_archive.py` | `total_export_manual_archive_test.py` | Records user-supplied archive URLs, service labels, statuses, timestamps, and notes. | String/metadata handling only; no archive check or submission. |
| Local media registration | `LOCAL_MEDIA_REGISTRATION_METADATA.md` | `total_export_local_media.py` | `total_export_local_media_test.py` | Registers user-supplied local paths, size/hash metadata, media-type labels, and notes. | Existing local files only; no download, probing, capture, or transcription. |
| Local media verification | `LOCAL_MEDIA_VERIFICATION_REPORT.md` | `total_export_local_media_verify.py` | `total_export_local_media_verify_test.py` | Rechecks local path existence, size, and optional SHA-256 against registration records. | Local filesystem only; missing files are not remote-source conclusions. |
| Local media verification CLI | `LOCAL_MEDIA_VERIFICATION_REPORT.md` | `total_export_local_media_verify_cli.py` | `total_export_local_media_verify_cli_test.py` | Loads local JSON records and renders verification as text, Markdown, or JSON. | Writes only with explicit `--output`; no provider or network use. |
| Preservation plan | `PRESERVATION_PLAN_REPORT.md` | `total_export_preservation_plan.py` | `total_export_preservation_plan_test.py` | Compares source URLs with manual archive and local media records to identify manual follow-up. | In-memory/local records only; recommendations do not trigger capture or checks. |
| Preservation plan CLI | `PRESERVATION_PLAN_REPORT.md` | `total_export_preservation_plan_cli.py` | `total_export_preservation_plan_cli_test.py` | Loads local preservation JSON and renders text, Markdown, or JSON plans. | Writes only with explicit `--output`; no archive, download, or network behavior. |
| Preservation metadata seed | `PRESERVATION_METADATA_SEED.md` | `PRESERVATION_METADATA_SEED.json` | `preservation_metadata_seed_test.py` | Supplies deterministic manual archive/local media examples for report checks. | Example data only; fake paths, hashes, and URLs are not verified evidence. |
| Preservation metadata seed report | `PRESERVATION_METADATA_SEED.md` | `preservation_metadata_seed_report.py` | `preservation_metadata_seed_report_test.py` | Loads the checked-in seed through existing builders and renders Markdown, text, or JSON. | Explicit-output-only local reporting; fake paths are not inspected or hashed. |
| Bundle index | `TOTAL_EXPORT_BUNDLE_INDEX.md` | `total_export_bundle_index.py` | `total_export_bundle_index_test.py` | Indexes local ZIP paths and sibling SHA-256/inspection sidecar state. | No ZIP extraction or internal ZIP reads; local files and sidecars only. |
| Bundle index CLI | `TOTAL_EXPORT_BUNDLE_INDEX.md` | `total_export_bundle_index_cli.py` | `total_export_bundle_index_cli_test.py` | Scans a local folder and renders bundle index text, Markdown, or JSON. | Writes only with explicit `--output`; no network or archive-service access. |
| Bundle index reconciliation | `TOTAL_EXPORT_BUNDLE_INDEX_RECONCILIATION.md` | `total_export_bundle_index_reconcile.py` | `total_export_bundle_index_reconcile_test.py` | Compares expected ZIP paths with an in-memory bundle index and reports missing, unexpected, or needs-review bundles. | Path/index comparison only; no extraction, fetching, or external validation. |
| Bundle index reconciliation CLI | `TOTAL_EXPORT_BUNDLE_INDEX_RECONCILIATION.md` | `total_export_bundle_index_reconcile_cli.py` | `total_export_bundle_index_reconcile_cli_test.py` | Loads JSON/text expected lists, builds a local index, reconciles it, and renders text, Markdown, or JSON. | Writes only with explicit `--output`; no extraction, network, or provider behavior. |

The broader phase boundaries and possible later work remain in `SOURCE_PRESERVATION_ROADMAP.md`. General Total Export package-shell developer commands remain in `TOTAL_EXPORT_DEV_CLI_EXAMPLES.md`.

## CLI Index

| CLI | Key flags | Input | Output | Write behavior | Boundary |
| --- | --- | --- | --- | --- | --- |
| `total_export_local_media_verify_cli.py` | `--input`, `--format`, `--no-compute-hash`, `--output`, `--overwrite` | Local JSON object/list of media records | Text, Markdown, JSON | Stdout by default; file only with `--output`; overwrite requires `--overwrite`. | Metadata/local-file verification only; no network, download, archive, provider, or GUI behavior. |
| `total_export_preservation_plan_cli.py` | `--input`, `--format`, `--output`, `--overwrite` | Local JSON with source URLs, archive records, and media records | Text, Markdown, JSON | Stdout by default; file only with `--output`; overwrite requires `--overwrite`. | Local planning only; no archive checks, source fetch, download, provider, or GUI behavior. |
| `preservation_metadata_seed_report.py` | `--input`, `--format`, `--output`, `--overwrite` | Local seed-shaped JSON; defaults to `PRESERVATION_METADATA_SEED.json` | Markdown, text, JSON | Stdout by default; file only with `--output`; overwrite requires `--overwrite`. | Example-report generation only; no path inspection, network, archive, provider, ZIP extraction, or GUI behavior. |
| `total_export_bundle_index_cli.py` | `--root`, `--format`, `--recursive`, `--no-compute-hash`, `--output`, `--overwrite` | Existing local folder containing ZIPs and sibling sidecars | Text, Markdown, JSON | Stdout by default; file only with `--output`; overwrite requires `--overwrite`. | No ZIP extraction, network, archive, provider, or GUI behavior. |
| `total_export_bundle_index_reconcile_cli.py` | `--root`, `--expected`, `--format`, `--recursive`, `--no-compute-hash`, `--output`, `--overwrite` | Local bundle folder plus JSON object/list or comment-aware text expected list | Text, Markdown, JSON | Stdout by default; file only with `--output`; overwrite requires `--overwrite`. | No ZIP extraction, network, download, archive, provider, or GUI behavior. |

There are currently no separate CLIs for creating manual archive records or local media registration records. Those modules expose deterministic Python metadata/report helpers only.

## Test Index

| Test | Coverage |
| --- | --- |
| `total_export_manual_archive_test.py` | Archive status normalization, local service-name detection, record/dict/report output, and no-service-call semantics. |
| `total_export_local_media_test.py` | Local record creation, extension-based media type, optional hash/size handling, and deterministic reports. |
| `total_export_local_media_verify_test.py` | Verified, missing, size mismatch, hash mismatch, needs-review, and not-checked local states. |
| `total_export_local_media_verify_cli_test.py` | JSON loading, text/Markdown/JSON output, hash-disabled mode, explicit output, overwrite protection, and invalid input. |
| `total_export_preservation_plan_test.py` | Source matching, archive/media presence, follow-up counts/actions, URL normalization, and deterministic output. |
| `total_export_preservation_plan_cli_test.py` | Local JSON parsing, all output formats, explicit output, overwrite protection, and invalid input. |
| `preservation_metadata_seed_test.py` | Seed shape and compatibility with archive/media records and preservation-plan rendering. |
| `preservation_metadata_seed_report_test.py` | Default seed loading, all output formats, explicit output, overwrite protection, and invalid input. |
| `total_export_bundle_index_test.py` | Complete/missing/mismatched/unreadable sidecars, recursive indexing, hashing, and reports. |
| `total_export_bundle_index_cli_test.py` | Local folder indexing, recursive/hash modes, all output formats, explicit output, and overwrite protection. |
| `total_export_bundle_index_reconcile_test.py` | Present, missing, unexpected, and sidecar-needs-review expected bundle states. |
| `total_export_bundle_index_reconcile_cli_test.py` | JSON object/list and text expected inputs, recursive/hash modes, all output formats, explicit output, and invalid input. |
| `youtube_url_utils_test.py` | Pure-local YouTube URL/video-ID normalization used by preservation source matching. |

All listed tests are script-style local self-tests. Their temporary files are created under `TemporaryDirectory`; they do not require network access.

## Local-Only Data Model Summary

### Manual Archive Records

`ManualArchiveRecord` stores a source URL, normalized URL, user-supplied archive URL, locally detected service label, user-entered status/timestamps, and notes. Archive statuses are local assertions such as `manually_supplied` or `manually_checked_not_found`; they are not external verification.

### Local Media Records

`LocalMediaRecord` stores the source relationship, package ID, user-selected local path, filename, size, optional SHA-256, extension-based media type, optional manual duration, timestamps, and notes. Registration can inspect/hash an explicitly selected local file, but it does not probe media or obtain files.

### Local Media Verification

`LocalMediaVerificationResult` compares registration metadata with current local filesystem state. Its states include `verified`, `missing_local_file`, `size_mismatch`, `sha256_mismatch`, `needs_review`, and `not_checked`.

### Preservation Plans

`PreservationPlanResult` groups normalized source URLs with matching archive/media records and produces manual follow-up warnings/actions. YouTube normalization uses `youtube_url_utils.py`; other source URLs remain cleaned local strings.

### Bundle Indexes

`BundleIndexResult` records local ZIP paths, size/hash data, sibling `.sha256` and `.inspection.json` state, warnings, and actions. `complete` means the expected local sidecars are present/readable and the computed ZIP hash matches; it is not a claim about source authenticity.

### Bundle Reconciliation

`BundleIndexReconciliationResult` compares `ExpectedBundleEntry` paths with a supplied local bundle index. It distinguishes `present`, `missing_expected_zip`, `present_needs_review`, and `unexpected_zip`. Missing and unexpected paths require manual review but do not establish deletion or invalidity.

## Completed Milestones

1. Documented local-only preservation phases and hard boundaries.
2. Added user-supplied manual archive URL metadata and local reports.
3. Added user-supplied local media registration metadata and local reports.
4. Added current-state local media verification and a text/Markdown/JSON CLI.
5. Added preservation-plan reporting and a text/Markdown/JSON CLI.
6. Added deterministic preservation metadata seed data and compatibility tests.
7. Added a deterministic Markdown/text/JSON seed report generator with explicit-output-only writes.
8. Added local bundle indexing and a text/Markdown/JSON CLI.
9. Added expected-bundle reconciliation and a text/Markdown/JSON CLI.

None of these milestones introduced source acquisition, external verification, archive-service access, or GUI integration.

## Deliberately Out Of Scope

- Automated archive lookup or submission.
- Source-page, comment, live-chat, caption, or metadata fetching.
- Media downloading, stream detection, or media probing.
- Screenshot capture, browser automation, and scraping.
- ASR execution or provider calls.
- ZIP extraction or inspection of file contents inside bundle ZIPs.
- Credential, key, cookie, or authenticated-session storage.
- GUI controls or background jobs for preservation workflows.
- Claims that missing local data proves anything about external availability or provenance.

## Recommended Next Safe Milestones

1. Design a manual local evidence-package manifest that references existing helper outputs without downloading, extracting ZIPs, checking archives, or calling providers.
2. Perform docs-only bundle/preservation index polish if names or boundaries drift.
3. Keep any networked archive, downloader, capture, or provider work deferred until separately approved with explicit opt-in and mocked/local tests.

## Verify The Local Preservation Stack

Run from the repository root with the project virtual environment active.

Compile the current preservation modules and tests:

```cmd
python -m py_compile total_export_manual_archive.py total_export_manual_archive_test.py total_export_local_media.py total_export_local_media_test.py total_export_local_media_verify.py total_export_local_media_verify_test.py total_export_local_media_verify_cli.py total_export_local_media_verify_cli_test.py total_export_preservation_plan.py total_export_preservation_plan_test.py total_export_preservation_plan_cli.py total_export_preservation_plan_cli_test.py preservation_metadata_seed_test.py total_export_bundle_index.py total_export_bundle_index_test.py total_export_bundle_index_cli.py total_export_bundle_index_cli_test.py total_export_bundle_index_reconcile.py total_export_bundle_index_reconcile_test.py total_export_bundle_index_reconcile_cli.py total_export_bundle_index_reconcile_cli_test.py youtube_url_utils.py youtube_url_utils_test.py
```

Run the local self-tests:

```cmd
python total_export_manual_archive_test.py & python total_export_local_media_test.py & python total_export_local_media_verify_test.py & python total_export_local_media_verify_cli_test.py & python total_export_preservation_plan_test.py & python total_export_preservation_plan_cli_test.py & python preservation_metadata_seed_test.py & python total_export_bundle_index_test.py & python total_export_bundle_index_cli_test.py & python total_export_bundle_index_reconcile_test.py & python total_export_bundle_index_reconcile_cli_test.py & python youtube_url_utils_test.py
```

Review repository consistency:

```cmd
git diff --check & git status --short
```

These checks use local files and temporary directories only. They must not be replaced with network-dependent tests.

## Codex Workflow Notes

- Start each milestone by checking `git status --short` and the latest commit. If a prompt requires a clean checkpoint and the tree is dirty, stop rather than layering unrelated work.
- Inspect the current local modules/docs before editing; filenames and behavior in the repository are authoritative.
- Keep one approved milestone per patch and avoid broad refactors.
- Use local/mocked script-style tests and `TemporaryDirectory`; do not consume API quota or require external services.
- Preserve explicit write behavior: CLIs print by default and write only when an output path is supplied; overwrites require an explicit flag.
- Treat unknown or missing metadata as uncertainty, not evidence of absence.
- Do not commit until the user approves the reviewed diff and checks.
