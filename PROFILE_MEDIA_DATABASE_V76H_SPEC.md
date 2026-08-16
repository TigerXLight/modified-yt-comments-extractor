# Profile/Media Database V76H — End-to-End Workflow Pack

V76H connects the Database-mode planning and execution layers into one UI-neutral workflow proof.

## Scope

V76H coordinates these existing layers:

1. V76E explicit folder-tree import planner.
2. Guarded standalone batch-preview JSON writing.
3. V76C/V76D explicit batch JSON GUI loading and refresh.
4. V76F controlled materialization.
5. V76G reviewed folder rename/move operations.
6. Implementation closeout/readiness reporting.

The workflow remains explicit-input only. It does not crawl a folder, infer contents from a real filesystem tree, import media automatically, copy media, download media, auto-classify identities, or infer sensitive identifiers.

## Confirmation phrases

The workflow exposes all exact phrases in one place:

- `WRITE_EXISTING_FOLDER_BATCH_PREVIEW`
- `MATERIALIZE_PROFILE_MEDIA_DATABASE_SELECTION`
- `APPLY_PROFILE_MEDIA_REVIEWED_FOLDER_OPERATIONS`

Writes and folder operations remain blocked unless the relevant exact phrase is supplied.

## New files

- `profile_media_database_end_to_end_workflow.py`
- `profile_media_database_end_to_end_workflow_test.py`
- `profile_media_database_implementation_closeout.py`
- `profile_media_database_implementation_closeout_test.py`
- `tools/run_profile_media_database_end_to_end_cli_v76h.py`
- `testdata/profile_media_database_v76h_end_to_end_tree_fixture.txt`
- `testdata/profile_media_database_v76h_folder_operations_fixture.json`
- `testdata/profile_media_database_v76h_large_end_to_end_tree_fixture.txt`
- `testdata/profile_media_database_v76h_end_to_end_acceptance_matrix.json`
- `testdata/profile_media_database_v76h_end_to_end_stress_matrix.json`

## Updated files

- `profile_media_database_workbench_panel.py`
- `profile_media_database_workbench_panel_test.py`

The panel receives a new action entry: `run_end_to_end_workflow_check`.

## Safety invariants

Default workflow behavior is dry-run preview only:

- `folder_scan_performed = false`
- `folder_creation_performed = false`
- `folder_move_performed = false`
- `folder_rename_performed = false`
- `file_copy_performed = false`
- `file_write_performed = false`
- `media_download_performed = false`
- `automatic_classification_performed = false`
- `sensitive_identifier_inference_performed = false`

Confirmed preview writing may set `file_write_performed = true` only for a standalone batch-preview JSON file.

Confirmed materialization may create the approved Database folder hierarchy and metadata files.

Confirmed folder operations may rename or move explicitly supplied folders inside `database_root` only.

## Implementation status after V76H

V76H makes the backend/GUI-neutral Database workflow ready for manual GUI smoke testing. The remaining work is final clickable GUI button wiring and one disposable-root manual test.
