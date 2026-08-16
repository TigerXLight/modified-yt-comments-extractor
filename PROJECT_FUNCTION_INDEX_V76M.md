# Project Function Index V76M

Audit date: 2026-08-16

This index highlights important modules and entrypoints. It is not a complete symbol dump. Network/folder/write behavior is reported from inspected code, not from roadmap claims.

Status basis: listed rows are current repository functions/classes and are therefore `IMPLEMENTED` unless the row notes `PARTIAL`, `CLI_ONLY`, `GUI_ONLY`, `REFERENCE_ONLY`, `BLOCKED_BY_DEPENDENCY`, or `NEEDS_MANUAL_REVIEW`.

## Source URL / Adapter / GUI State

| File | Purpose | Key functions/classes | Inputs | Outputs | Writes files/folders | Network/web download | Folder scan | Confirmation token | Related tests |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `source_adapters.py` | URL adapter recognition and method metadata | `YouTubeSourceAdapter`, `MsnSourceAdapter`, `TwitterXSourceAdapter`, `SourceMethodProfile` | URL strings | adapter id, source id, method profile metadata | no | no | no | none | `source_adapters_test.py` |
| `source_resource_state.py` | Source URL row/resource state | `SourceResourceRowState`, `normalize_source_url_token`, source intake helpers | pasted URLs/text | row states, archive/resource states | no | no | no | none | `source_resource_state_test.py` |
| `source_url_files_bridge.py` | App-facing URL/FILES bridge | bridge state builders | source/resource state | panel state | no | no | no | none | `source_url_files_bridge_test.py` |
| `source_twitter_compact_row.py` | X/Twitter compact row state | row/settings state helpers | X/Twitter source metadata | compact row view state | no | no | no | none | `source_twitter_compact_row_test.py`, `tools/assert_twitter_x_*.py` |
| `main.py` | Main app integration surface | GUI/controller functions | app state and user input | app UI state/actions | yes, through invoked workflows | depends on invoked workflow | depends on invoked workflow | workflow-specific | `main_source_resource_ui_test.py`, `main_export_state_test.py` |

## YouTube / JDownloader / Media

| File | Purpose | Key functions/classes | Inputs | Outputs | Writes files/folders | Network/web download | Folder scan | Confirmation token | Related tests |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `youtube_url_utils.py` | YouTube URL parsing | `extract_youtube_video_id`, `normalize_youtube_url` | URL | video id/canonical URL | no | no | no | none | `youtube_url_utils_test.py` |
| `youtube_gui_media_queue.py` | GUI media queue and metadata writes | `queue_youtube_gui_source_row_selection` | selected row, preferences | queue result, metadata files | yes, queue output | via selected backend | no | none | `youtube_gui_media_queue_test.py` |
| `youtube_media_download_backend.py` | Shared/backend YouTube media route | backend models/functions | media URL/job config | backend result | yes | yes when invoked | no | backend-specific | `youtube_media_download_backend_test.py` |
| `jdownloader_internal_cnl.py` | Local JD route submission | `submit_api3128_download_route`, `submit_api3128_then_flashgot_fallback`, `submit_cnl_multiroute` | URL/package/output dir | route attempts/manifest metadata | no direct media writes; JD writes downloads | localhost JD API | output/job polling | JD runtime config | `jdownloader_internal_cnl_test.py`, `tools/assert_jdownloader_api3128_fast_route_v64.py` |
| `jdownloader_internal_job.py` | Internal JD job orchestration | `build_youtube_job_request`, `run_internal_youtube_job` | source URL/output dir | manifest/result | yes | localhost JD route | output folder monitoring | none | `jdownloader_internal_job_test.py` |
| `jdownloader_internal_download_monitor.py` | Download folder monitoring | monitor helpers | output dir | file records/timing | no | no | yes, target output only | none | `jdownloader_internal_download_monitor_test.py` |
| `source_media_execution_bridge.py` | Generic media copy/download/mux wrappers | `copy_selected_local_media_files`, `download_selected_media_resources_with_http_client`, `execute_ffmpeg_mux_plan`, `execute_yt_dlp_command` | selected media/commands | receipts/results | yes | injectable HTTP / subprocess when approved | explicit paths only | operator approval upstream | `source_media_execution_bridge_test.py` |

## ASR / Access / Keys

| File | Purpose | Key functions/classes | Inputs | Outputs | Writes files/folders | Network/web download | Folder scan | Confirmation token | Related tests |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `asr_tools.py` | Local transcription helper | `transcribe_media_file` | media path/profile options | transcript/report | yes | no provider call by itself | explicit media path only | none | `asr_tools_test.py` |
| `asr_whispercpp.py` | whisper.cpp integration helpers | capability/runtime helpers | binary/media paths | ASR result/capability data | yes when invoked | no | explicit paths only | none | `asr_whispercpp_cleanup_test.py` |
| `online_asr_execution_gate.py` | Online ASR readiness gate | `build_online_asr_execution_gate_plan` | provider catalogue/status | readiness summary | no | no | no | approval required for execution elsewhere | `online_asr_execution_gate_test.py` |
| `access_keys_catalog.py` | Provider catalogue | catalogue builders | none | provider metadata | no | no | no | none | `access_keys_catalog_test.py` |
| `access_keys_view_model.py` | Access & Keys UI view model | view-model builders | provider state | UI state | no | no | no | none | `access_keys_view_model_test.py` |

## Browser Capture / Archive / Replay

| File | Purpose | Key functions/classes | Inputs | Outputs | Writes files/folders | Network/web download | Folder scan | Confirmation token | Related tests |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `source_local_browser_execution.py` | Local/fixture browser execution | `run_local_fixture_browser_execution`, `build_protected_black_output_result` | local file/localhost URL | DOM/screenshot artifacts | yes | local/fixture only in tests | no | operator gateway for broader use | `source_local_browser_execution_test.py` |
| `capture_warc_wacz.py` | WARC/WACZ helpers | WARC/WACZ functions | local records | archive files | yes | no | no | none | `capture_warc_wacz_test.py` |
| `source_archive_execution_bridge.py` | Archive clients/wrappers | Wayback/archive.today request builders, `execute_archive_http_request`, ArchiveBox plan/command execution | target URL/http client/command runner | requests/results | yes for command output | only through injected/approved client | no | explicit submit/command approval | `source_archive_execution_bridge_test.py` |
| `source_offline_bundle_writer.py` | Offline evidence ZIP writer | `write_offline_evidence_bundle` | evidence inputs | compressed bundle | yes | no | no | none | `source_offline_bundle_writer_test.py` |
| `source_local_webpage_viewer.py` | Offline local viewer bundle | `write_local_webpage_viewer` | capture dir/files | index HTML/open scripts | yes | no | capture dir listing only | none | `source_local_webpage_viewer_test.py` |
| `source_replay_static_snapshot.py` | Static evidence/page/text replay views | static page builders and WARC writers | local evidence metadata | HTML/TXT/MD/WARC | yes | no | no | none | `source_replay_static_snapshot_test.py` |

## MSN

| File | Purpose | Key functions/classes | Inputs | Outputs | Writes files/folders | Network/web download | Folder scan | Confirmation token | Related tests |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `msn_source_adapter.py` | Production MSN adapter workflow | `run_msn_closeout_validation`, `capture_msn_android_comments_stitched_screenshot`, `capture_msn_android_article_screenshot`, `download_msn_article_media`, `write_york_source_role_sidecars` | MSN URL/output dir/options | comments/profile exports, screenshots, media receipts, closeout report | yes | yes when live/browser/media flags invoked | no | operator-controlled CLI flags | `msn_source_adapter_test.py` |
| `source_msn_comments_profile_export.py` | V34/V35-style comments/profile export | export builders | comments/profile JSON rows | JSON/TXT/MD/HTML/profiles | yes | no | no | none | `source_msn_comments_profile_export_test.py` |
| `source_msn_live_viewable_capture_cli.py` | Side-by-side live viewable capture CLI | `run_live_viewable_capture` | target URL/output dir | rendered page, WARC/WACZ, validation JSON, viewer | yes | yes when run | no | target URL safety gate | `source_msn_live_viewable_capture_test.py` |
| `source_msn_rendered_browser_validation.py` | MSN rendered browser validation | validation runner | approved MSN URL | browser validation bundle | yes | yes when run | no | URL gate | `source_msn_rendered_browser_validation_test.py` |

## Twitter / X

| File | Purpose | Key functions/classes | Inputs | Outputs | Writes files/folders | Network/web download | Folder scan | Confirmation token | Related tests |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `twitter_browser_capture_strategy.py` | Browser capture planning | strategy builders | X/Twitter URL | capture plan/session config | no | no | no | none | `twitter_browser_capture_strategy_test.py` |
| `twitter_browser_capture_runner.py` | Browser capture result assembly | `TwitterBrowserCaptureRunResult`, runner helpers | plan/executor | JSON/DOM/screenshot/media inventory | yes | browser/session when invoked | no | caller/operator controlled | `twitter_browser_capture_runner_test.py` |
| `twitter_browser_timeline_pagination.py` | Timeline pagination parsing | cursor/entry extraction | HAR/body JSON | timeline rows/cursors | no | no | no | none | `twitter_browser_timeline_pagination.py` plus assertion tools |
| `twitter_timeline_cursor_scheduler.py` | Cursor-driven scheduler | scheduler result/manifest builders | seed capture/cursors | JSONL/state/manifest | yes | browser-fetch cursor when invoked | no | caller/operator controlled | `tools/assert_twitter_cursor_*.py` |
| `twitter_media_backend.py` | Shared media backend for Twitter | media backend runner | media URLs/backend config | media backend result | yes | yes when invoked | no | backend/operator controlled | `twitter_media_backend_test.py` |

## Total Export / Source Evidence / Evidence Database

| File | Purpose | Key functions/classes | Inputs | Outputs | Writes files/folders | Network/web download | Folder scan | Confirmation token | Related tests |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `total_export_manifest.py` | Total Export manifest schema | `TotalExportManifest`, `ExportAsset` | asset/provenance data | manifest JSON | yes through writer helpers | no | no | none | `total_export_manifest_test.py` |
| `total_export_package.py` | Package writing | package helpers | manifest/assets | package folder/files | yes | no | explicit files | none | `total_export_package_test.py` |
| `source_evidence_workflow_state.py` | Source Evidence app-facing state | `SourceEvidenceWorkflowState` | source config/default builders | bundled sidecar state | no by itself | no | no | none | `source_evidence_workflow_state_test.py` |
| `source_evidence_workflow_store.py` | Workflow sidecar persistence | store helpers | workflow state/output path | JSON sidecars | yes | no | no | none | `source_evidence_workflow_store_test.py` |
| `source_evidence_review_export.py` | Review manifest export | review manifest builders | workflow/review data | review manifest | yes via callers | no | no | none | `source_evidence_review_export_test.py` |
| `evidence_database_index.py` | Evidence index scan/model | scan/index helpers | explicit paths/records | index records | no/scan explicit roots | no | yes when called | none | `evidence_database_index_test.py` |
| `evidence_movement_approval.py` | Movement approval/execution | preview, token, execute, receipt builders | source/destination paths | receipts/copied/moved files | yes when executed | no | explicit files only | approval token | `evidence_movement_approval_test.py` |

## Profile / Media Database

| File | Purpose | Key functions/classes | Inputs | Outputs | Writes files/folders | Network/web download | Folder scan | Confirmation token | Related tests |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `profile_media_database.py` | Core Profile/Media records | database models/helpers | explicit payloads | records/reports | no | no | no | none | `profile_media_database_test.py` |
| `profile_media_home_repository_model.py` | HOME path model | `parse_home_classification_path` | classification path text | parsed HOME path | no | no | no | none | `profile_media_home_repository_model_test.py` |
| `profile_media_source_role_policy.py` | Source-role normalization | `normalize_source_role_value`, `canonical_source_role` | role strings | normalized role/policy report | no | no | no | none | `profile_media_source_role_policy_test.py` |
| `profile_media_source_criticism_model.py` | Structural source criticism | `build_evidence_marking`, `evaluate_structural_source_criticism` | evidence markings | candidate review lane/role | no | no | no | none | `profile_media_source_criticism_model_test.py` |
| `profile_media_existing_folder_batch_planner.py` | Existing folder import planner | `build_existing_folder_to_batch_plan`, `write_batch_preview_if_confirmed` | explicit folder-tree text | dry-run batch preview | optional preview JSON | no | no real folder scan | `WRITE_EXISTING_FOLDER_BATCH_PREVIEW` | `profile_media_existing_folder_batch_planner_test.py` |
| `profile_media_database_materialize_workflow.py` | Controlled Save-to-HOME backend | `build_database_materialize_plan`, `apply_database_materialize_plan` | explicit batch JSON paths | dry-run/result | yes when confirmed | no | no | `MATERIALIZE_PROFILE_MEDIA_DATABASE_SELECTION` | `profile_media_database_materialize_workflow_test.py` |
| `profile_media_database_folder_operations.py` | Reviewed folder ops | `build_folder_operations_plan`, `apply_folder_operations_plan` | explicit operation JSON | dry-run/result | yes when confirmed | no | no | `APPLY_PROFILE_MEDIA_REVIEWED_FOLDER_OPERATIONS` | `profile_media_database_folder_operations_test.py` |
| `profile_media_database_end_to_end_workflow.py` | End-to-end proof coordinator | `run_profile_media_database_end_to_end_workflow`, `confirmation_phrases` | explicit tree/batch/operation inputs | combined proof result | optional writes when confirmed | no | no | three exact phrases exposed | `profile_media_database_end_to_end_workflow_test.py` |
| `profile_media_article_extraction_adapter.py` | Offline article extraction adapter | `extract_article_from_html`, `extract_article_from_file`, `write_article_source_preview` | supplied HTML/local file | metadata/text/source preview | optional JSON | no | no | `WRITE_ARTICLE_EXTRACTION_SOURCE_PREVIEW` | `profile_media_article_extraction_adapter_test.py` |
