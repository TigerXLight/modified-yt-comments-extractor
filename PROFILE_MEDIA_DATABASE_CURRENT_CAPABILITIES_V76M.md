# Profile Media Database Current Capabilities V76M

Audit date: 2026-08-16

This document focuses on the current Profile/Media Database HOME repository mode and source-criticism work.

## Current User-Facing Model

- `IMPLEMENTED`, `TESTED`: DATABASE/HOME repository mode is represented through `profile_media_database_mode.py`, `profile_media_database_runtime.py`, GUI state modules, and `profile_media_home_repository_model.py`.
- `IMPLEMENTED`, `TESTED`: HOME is classification-driven. A case is action/event/type/time/source-context driven, not simply a person.
- `IMPLEMENTED`, `TESTED`: Workbench/panel helpers expose Add/Import, Save to HOME, review moves, update saved index, and HOME metrics. Backend code may still use the older term `materialize`; user-facing docs should prefer "Save to HOME" or "controlled folder/index creation."
- `IMPLEMENTED`, `TESTED`: Batch JSON exists as an internal/intermediate format and CLI proof path. It should not be presented as the normal user workflow.

## Source Role And Source Criticism

- `IMPLEMENTED`, `TESTED`: Source-role normalization exists in `profile_media_source_role_policy.py`.
- `IMPLEMENTED`, `TESTED`: Structural source-criticism decisions exist in `profile_media_source_criticism_model.py`, including `claim_subject_affiliation_gap`.
- `IMPLEMENTED`, `TESTED`: Article extraction produces `source_role_candidate`, `source_role_is_final=False`, `review_lanes`, attribution markings, and source-basis candidates.
- `PARTIAL`: The system preserves review lanes and candidates; it does not make final product classification decisions automatically.
- `PARTIAL`: Most news articles are not automatically secondary. Secondary depends on witness/direct connectivity. Repeated police, court, family, agency, or publisher claims are usually tertiary unless a direct witness/holder/interviewer basis exists.
- `DOCUMENTED_ONLY`: FEVER, AVeriTeC, MICE, benchmark verdict logic, and dataset-scoring concepts are not product classification logic in current code.

## Persons / Review Items / Case Paths

- `IMPLEMENTED`, `TESTED`: `profile_media_database.py`, `profile_media_profile_intake.py`, and `profile_media_source_intake.py` model profile/source intake data.
- `IMPLEMENTED`, `TESTED`: `profile_media_case_manifest.py`, `profile_media_case_batch.py`, and `profile_media_case_workspace.py` model explicit case/source/profile plans.
- `IMPLEMENTED`, `TESTED`: `profile_media_home_repository_model.py` parses HOME classification paths and explains why a case/event is not merely a person.
- `PARTIAL`: Segment-level first-person "I" logic is not a full implemented classifier in the audited modules. Review lanes can preserve that need, but final assignment remains human-reviewed.

## Existing Folder Import

- `IMPLEMENTED`, `TESTED`: `profile_media_existing_folder_batch_planner.py` converts explicit folder-tree text into a dry-run batch preview.
- `IMPLEMENTED`, `TESTED`: It does not crawl the user's HOME folder. It uses caller-supplied tree lines and can write a standalone preview only with `WRITE_EXISTING_FOLDER_BATCH_PREVIEW`.
- `PARTIAL`: Full direct reading of `source.txt`, RTF files, and media source folders from a real HOME tree is not established as implemented by this audit.

## Save To HOME / Folder Operations

- `IMPLEMENTED`, `TESTED`: Controlled Save-to-HOME backend is in `profile_media_database_materialize_workflow.py`; code uses `MATERIALIZE_PROFILE_MEDIA_DATABASE_SELECTION`.
- `IMPLEMENTED`, `TESTED`: Reviewed folder rename/move operations are in `profile_media_database_folder_operations.py`; execution requires `APPLY_PROFILE_MEDIA_REVIEWED_FOLDER_OPERATIONS`.
- `IMPLEMENTED`, `TESTED`: Reconciliation after folder operations is present in `profile_media_database_operation_reconciliation.py`.
- `PARTIAL`, `NEEDS_MANUAL_REVIEW`: These workflows operate on explicit inputs and guarded paths. They are not an unattended real HOME ingestion engine.

## Article Extraction Adapter V76L

- `IMPLEMENTED`, `TESTED`: `profile_media_article_extraction_adapter.py` accepts supplied HTML text or a local HTML file.
- `IMPLEMENTED`, `TESTED`: Stdlib fallback parsing extracts title/H1/body-ish text/meta/links/images.
- `PARTIAL`, `BLOCKED_BY_DEPENDENCY`: Optional `metadata_parser`, `trafilatura`, and `newspaper4k` extractors are attempted by import name. If not installed or not importable, runs are marked skipped/unavailable and the stdlib fallback remains deterministic.
- `REFERENCE_ONLY`: `external_reference_sources_20260816_article_extraction/` contains downloaded reference repos and is not committed app code.
- `IMPLEMENTED`, `TESTED`: Writing an article source preview JSON requires `WRITE_ARTICLE_EXTRACTION_SOURCE_PREVIEW`.
- `PARTIAL`: Extraction libraries gather metadata/content. They do not decide final Primary/Secondary/Tertiary role.

## GUI State

- `IMPLEMENTED`, `TESTED`: GUI panel state exists in `profile_media_database_workbench_panel.py`.
- `IMPLEMENTED`, `TESTED`: GUI controller/state persistence exists in `profile_media_database_gui_controller.py` and `profile_media_database_gui_state_store.py`.
- `IMPLEMENTED`, `TESTED`: GUI smoke readiness and main integration tests exist.
- `PARTIAL`: Full visual GUI QA still needs manual smoke review for layout/flow.

## What Is Still Not Implemented Or Only Partial

- `PARTIAL`, `BLOCKED_BY_DEPENDENCY`: Full required dependency integration for `trafilatura`, `newspaper4k`, and `metadata_parser` is optional/import-based; the dependencies are not vendored.
- `PARTIAL`: Full HOME ingestion from real folders is not implemented as an automatic scan. Current paths use explicit tree text, explicit batch JSON, and confirmation-gated operations.
- `PARTIAL`: Direct source.txt + RTF + media source folder reading is not proven implemented by current source modules.
- `PARTIAL`: Segment-level first-person "I" logic is not a final classifier.
- `PARTIAL`: Social-media/video provenance is represented elsewhere in source adapter/Twitter/MSN modules, but not fully integrated as automatic Profile/Media HOME ingestion.
- `PARTIAL`: GUI Add/Import is represented as state/workbench actions; a complete end-user import wizard with all file formats remains future work unless paired with a specific current module/test.

