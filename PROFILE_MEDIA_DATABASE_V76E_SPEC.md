# Profile/Media Database V76E - Existing Folder Import Planner Pack

V76E adds a dry-run path from an already organised folder tree to a reviewable Profile/Media batch JSON preview. It also normalises the legacy `SECONDARY_WITNESS_SOURCE` alias to the canonical project role `SECONDARY_WITNESS_ACCOUNT`.

## Added

- `profile_media_source_role_policy.py`
- `profile_media_source_role_policy_test.py`
- `profile_media_existing_folder_batch_planner.py`
- `profile_media_existing_folder_batch_planner_test.py`
- `profile_media_existing_folder_gui_adapter.py`
- `tools/run_profile_media_existing_folder_planner_cli_v76e.py`
- `testdata/profile_media_database_v76e_existing_tree_fixture.txt`
- `testdata/profile_media_database_v76e_large_existing_tree_fixture.txt`
- `testdata/profile_media_database_v76e_existing_folder_acceptance_matrix.json`

## Updated

- `profile_media_source_intake.py` now accepts `SECONDARY_WITNESS_SOURCE` as a legacy alias and normalises it to `SECONDARY_WITNESS_ACCOUNT`.
- `profile_media_database_index.py` normalises source-role aliases in source and profile rows and emits explicit alias warnings.
- `profile_media_database_workbench_panel.py` exposes a main-workbench action for planning existing-folder imports. This is not a sidebar filter or preview.

## Safety

Default V76E behavior is dry-run/read-only. It does not scan folders. The folder tree must be provided explicitly as text lines.

The pack does not perform folder creation, folder moves, folder renames, file copies, media downloads, automatic classification, or sensitive identifier inference.

Standalone preview JSON writing is blocked unless the caller passes the exact confirmation phrase:

```text
WRITE_EXISTING_FOLDER_BATCH_PREVIEW
```

Even that write creates only a standalone preview file chosen by the caller; it does not mutate a case folder.

## Acceptance matrix

The acceptance matrix fixture contains deterministic rows proving bucket recognition, role-alias normalization expectations, and dry-run safety flags at larger scale.
