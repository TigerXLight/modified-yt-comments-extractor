# Project Current Capabilities And Functions V76M

Audit date: 2026-08-16

Audited branch: `v2.6.0-asr-engines`

Audited HEAD: `2710660 Add profile media article extraction adapter`

Scope: this document records implemented and testable capabilities visible in the repository source tree. It does not treat roadmap prose, external reference repos, or older handoff notes as implemented unless matching code/tests/CLI exist.

Status tags used here: `IMPLEMENTED`, `PARTIAL`, `CLI_ONLY`, `GUI_ONLY`, `TESTED`, `DOCUMENTED_ONLY`, `REFERENCE_ONLY`, `SUPERSEDED`, `BLOCKED_BY_DEPENDENCY`, `NEEDS_MANUAL_REVIEW`.

## Safety Baseline

- `IMPLEMENTED`, `TESTED`: Read-only audit and planning layers consistently expose flags such as `folder_scan_performed`, `media_download_performed`, `web_download_performed`, `automatic_classification_performed`, and `sensitive_identifier_inference_performed`.
- `IMPLEMENTED`, `TESTED`: Operator approval gating exists in `source_operator_approval_gateway.py` for local/temp execution, user-evidence execution, live external execution, archive submit, subprocess execution, and ASR readiness.
- `IMPLEMENTED`, `TESTED`: Evidence movement execution exists in `evidence_movement_approval.py` with preview, approval token, copy/move mode, hash verification, collision policy, and completed-evidence receipt. This is not automatic database ingestion.
- `REFERENCE_ONLY`: `external_reference_sources_20260816_article_extraction/` is an untracked folder of external reference repos. It is not committed and is not app code.

## YouTube And Media Download / Export

- `IMPLEMENTED`, `TESTED`: YouTube URL normalization and video ID handling exist in `youtube_url_utils.py` and tests.
- `IMPLEMENTED`, `TESTED`: YouTube GUI media queue planning and manifest integration exist in `youtube_gui_media_queue.py`.
- `IMPLEMENTED`, `TESTED`: Internal JDownloader route support exists in `jdownloader_internal_cnl.py`, `jdownloader_internal_job.py`, and `jdownloader_internal_download_monitor.py`, including local Deprecated API 3128 route and `/flashgot` fallback assertions under `tools/`.
- `IMPLEMENTED`, `CLI_ONLY`, `TESTED`: JDownloader helper scripts exist under `tools/jdownloader/` and source/vendor management exists under `third_party/jdownloader/`.
- `IMPLEMENTED`, `TESTED`: Shared media execution bridges exist in `source_media_execution_bridge.py` for selected local media copy, injectable HTTP client download, FFmpeg mux wrapper, yt-dlp wrapper, dry-run, dependency-not-found, timeout/cancel, and redacted command result handling.
- `PARTIAL`, `NEEDS_MANUAL_REVIEW`: Runtime success and speed depend on the local JDownloader installation/configuration. The code preserves fallback routes and does not guarantee every platform media URL resolves.

## ASR / Local And Online Speech Recognition

- `IMPLEMENTED`, `TESTED`: Local ASR capability and defaults modules exist, including `asr_tools.py`, `asr_defaults.py`, `local_asr_capabilities.py`, `asr_whispercpp.py`, and report CLIs/tests.
- `IMPLEMENTED`, `TESTED`: Online ASR readiness and provider-gate summaries exist in `online_asr_execution_gate.py`, `access_online_asr_bridge.py`, and Access/Keys view-model modules.
- `IMPLEMENTED`, `TESTED`: Online provider UI/state code preserves credential-safe readiness. It does not run providers or read secrets through the summary layers.
- `NEEDS_MANUAL_REVIEW`: Actual ASR runtime depends on local binaries, media input, and provider credentials/configuration. This audit did not execute ASR.

## Screenshots / Browser Captures / Page Captures

- `IMPLEMENTED`, `TESTED`: Local/fixture browser execution exists in `source_local_browser_execution.py` with Playwright availability detection and deterministic local fallback artifacts.
- `IMPLEMENTED`, `TESTED`: Capture contracts/status/page outline/article/comments/livechat/media/snapshots modules exist under `capture_*.py`.
- `IMPLEMENTED`, `TESTED`: Screenshot result models include faithful/derived/protected labels in capture and local browser modules.
- `IMPLEMENTED`, `TESTED`: Unified job and app/operator controller layers exist in `source_unified_execution_runner.py` and `source_app_operator_controller.py`.
- `PARTIAL`, `NEEDS_MANUAL_REVIEW`: Live browser capture is gated and site-specific. Fixture/local tests do not prove external-site completeness.

## Offline Archive / Viewer / Replay / MSN Work

- `IMPLEMENTED`, `TESTED`: WARC/WACZ writing helpers exist in `capture_warc_wacz.py`.
- `IMPLEMENTED`, `TESTED`: Archive provider request builders and injectable-client execution exist in `source_archive_execution_bridge.py`, with Wayback/archive.today check/submit request builders and ArchiveBox command wrappers.
- `IMPLEMENTED`, `TESTED`: Local offline bundle writing exists in `source_offline_bundle_writer.py`.
- `IMPLEMENTED`, `TESTED`: Local webpage viewer output exists in `source_local_webpage_viewer.py`.
- `IMPLEMENTED`, `TESTED`: Static ReplayWeb fallback/evidence/page/text views exist in `source_replay_static_snapshot.py`.
- `IMPLEMENTED`, `TESTED`, `NEEDS_MANUAL_REVIEW`: MSN production adapter code exists in `msn_source_adapter.py`, including URL parsing, V15/V6 metadata, headless/default browser capture entrypoints, comments/profile exports, media receipt/download logic, offline archive status fields, source-role sidecars, and closeout reporting.
- `NEEDS_MANUAL_REVIEW`: WARC/WACZ replay success must not be inferred from generation. The code distinguishes generated from replay-tested status.

## Twitter / X Capture And Timeline Tools

- `IMPLEMENTED`, `TESTED`: X/Twitter URL adapter metadata exists in `source_adapters.py`.
- `IMPLEMENTED`, `TESTED`: Compact row state helpers exist in `source_twitter_compact_row.py` with assertion scripts in `tools/`.
- `IMPLEMENTED`, `CLI_ONLY`, `TESTED`: Browser capture strategy/runner/inspector modules exist in `twitter_browser_capture_strategy.py`, `twitter_browser_capture_runner.py`, and `twitter_browser_capture_inspector.py`.
- `IMPLEMENTED`, `CLI_ONLY`, `TESTED`: Timeline cursor and pagination tooling exists in `twitter_browser_timeline_pagination.py`, `twitter_timeline_cursor_scheduler.py`, and `tools/run_twitter_timeline_*.py`.
- `IMPLEMENTED`, `TESTED`: Shared media backend integration exists in `twitter_media_backend.py`.
- `PARTIAL`, `NEEDS_MANUAL_REVIEW`: Browser-session capture and cursor tools can be operational but are rate-limit/session sensitive. They are not a guarantee of complete X/Twitter capture in this audit.

## Total Export / Source Evidence / Manifest Workflows

- `IMPLEMENTED`, `TESTED`: Total Export manifest and package helpers exist in `total_export_manifest.py`, `total_export_package.py`, `total_export_prepare.py`, `total_export_review_bundle.py`, and related tests.
- `IMPLEMENTED`, `TESTED`: Source evidence workflow state/store/export sidecars exist in `source_evidence_workflow_state.py`, `source_evidence_workflow_store.py`, and `source_evidence_review_export.py`.
- `IMPLEMENTED`, `TESTED`: Source evidence queues, release plans, review manifests, grabbed records, receipt import/review, operator command packs, manual smoke checklists, selector approval packets, and named-site method packs exist under `source_*`.
- `PARTIAL`: The workflow includes many fixture and metadata-backed paths. Completion of real site/evidence capture depends on explicit operator approval and site-specific runtimes.

## Evidence Database And Review

- `IMPLEMENTED`, `TESTED`: Evidence database index/review/IO/taxonomy modules exist in `evidence_database_index.py`, `evidence_database_review.py`, `evidence_database_review_io.py`, and `evidence_database_taxonomy.py`.
- `IMPLEMENTED`, `TESTED`: Database operator workflow exists in `evidence_database_operator_workflow.py`.
- `IMPLEMENTED`, `TESTED`: Evidence movement approval and completed-evidence receipt code exists in `evidence_movement_approval.py`.
- `PARTIAL`, `NEEDS_MANUAL_REVIEW`: These workflows are explicit and guarded. This audit did not scan a real user evidence database HOME folder.

## Profile / Media Database HOME Repository Mode

- `IMPLEMENTED`, `TESTED`: HOME repository path parsing and classification path helpers exist in `profile_media_home_repository_model.py`.
- `IMPLEMENTED`, `TESTED`: Source-role policy and source-criticism model exist in `profile_media_source_role_policy.py` and `profile_media_source_criticism_model.py`.
- `IMPLEMENTED`, `TESTED`: Existing-folder import planner exists in `profile_media_existing_folder_batch_planner.py`, but it consumes explicit folder-tree text, not an automatic user media scan.
- `IMPLEMENTED`, `TESTED`: Workbench/panel/runtime/session/search/index/dashboard/view-model layers exist in `profile_media_database_*.py`.
- `IMPLEMENTED`, `TESTED`: Controlled save-to-HOME backend still uses the older backend term `materialize` in code, guarded by confirmation. User-facing docs should call this "Save to HOME" or "controlled folder/index creation."
- `IMPLEMENTED`, `TESTED`: Reviewed folder operations exist and require `APPLY_PROFILE_MEDIA_REVIEWED_FOLDER_OPERATIONS`.
- `IMPLEMENTED`, `TESTED`: End-to-end proof workflow exists in `profile_media_database_end_to_end_workflow.py`.
- `PARTIAL`: GUI Add/Import is represented through state and workbench panel helpers. Full rich ingestion of `source.txt`, RTF, media source folders, and social/video provenance remains a gap unless represented by explicit current modules.

## Article Extraction Adapter

- `IMPLEMENTED`, `TESTED`: `profile_media_article_extraction_adapter.py` parses supplied HTML/local HTML files and produces metadata/content/source-criticism preview fields.
- `CLI_ONLY`, `TESTED`: `tools/run_profile_media_article_extraction_cli_v76l.py` runs a deterministic proof and can write source preview JSON only with `WRITE_ARTICLE_EXTRACTION_SOURCE_PREVIEW`.
- `BLOCKED_BY_DEPENDENCY`, `REFERENCE_ONLY`: `metadata_parser`, `trafilatura`, and `newspaper4k` are optional extractor names. The app falls back to stdlib HTML parsing when they are unavailable. The external reference repos are not vendored.
- `PARTIAL`: Extraction libraries collect text and metadata; they do not make final Primary/Secondary/Tertiary role decisions.

## GUI Components

- `IMPLEMENTED`, `TESTED`: `main.py` includes the main app integration surface and has focused GUI state tests such as `main_source_resource_ui_test.py` and `main_export_state_test.py`.
- `IMPLEMENTED`, `TESTED`: Source URL / FILES bridge state exists in `source_url_files_bridge.py` and `source_resource_state.py`.
- `IMPLEMENTED`, `TESTED`: Profile/Media Database GUI panel/workbench/state helpers exist under `profile_media_database_*`.
- `IMPLEMENTED`, `TESTED`: Access & Keys and online ASR view-model/dialog layers exist.
- `PARTIAL`: Full GUI visual behavior should still be manually smoke-tested where tests are model/state focused.

## CLI Tools

- `IMPLEMENTED`, `CLI_ONLY`, `TESTED`: Many CLI entrypoints are present under `tools/`, including Profile/Media V75/V76 workflows, Twitter capture/cursor runners, JDownloader scripts, and source/MSN/local archive CLIs.
- `IMPLEMENTED`, `CLI_ONLY`: Most CLIs are deterministic wrappers around explicit inputs and confirmation phrases.
- `NEEDS_MANUAL_REVIEW`: CLIs that can run browser/network/subprocess actions require operator context and should not be treated as automatically safe in unattended runs.

## Confirmation Gates

- `WRITE_ARTICLE_EXTRACTION_SOURCE_PREVIEW`: required to write Profile/Media article source preview JSON.
- `WRITE_EXISTING_FOLDER_BATCH_PREVIEW`: required to write existing-folder batch preview JSON.
- `MATERIALIZE_PROFILE_MEDIA_DATABASE_SELECTION`: backend confirmation for controlled Save-to-HOME folder/metadata creation.
- `APPLY_PROFILE_MEDIA_REVIEWED_FOLDER_OPERATIONS`: required for reviewed folder rename/move operations.
- Operator approval tokens in `source_operator_approval_gateway.py`: required for live external, user-evidence, subprocess, archive submit, and ASR execution scopes.

## Tests And Fixtures

- `IMPLEMENTED`, `TESTED`: The repo has direct Python self-tests for most modules. This audit does not assume pytest.
- `IMPLEMENTED`, `TESTED`: Profile/Media fixtures exist under `testdata/profile_media_database_v*.json` and related text fixtures.
- `REFERENCE_ONLY`: external article extraction source repos remain outside git and should not be staged.

