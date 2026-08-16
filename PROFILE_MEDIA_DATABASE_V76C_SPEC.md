# Profile/Media Database V76C — Main GUI Workbench Panel

V76C begins GUI integration for the Profile/Media Database architecture.

## Scope

This pack adds a main-window Database workbench panel while preserving the
sidebar as a mode-only control.

The sidebar still only contains:

```text
DATABASE On / Off
FILES
```

The new panel belongs to the main content area, not the sidebar.

## Added files

```text
profile_media_database_workbench_panel.py
profile_media_database_workbench_panel_test.py
profile_media_database_batch_import_assistant.py
profile_media_database_batch_import_assistant_test.py
profile_media_database_gui_panel_main_test.py
tools/run_profile_media_database_gui_panel_cli_v76c.py
testdata/profile_media_database_v76c_gui_batch_fixture.json
testdata/profile_media_database_v76c_large_gui_stress_fixture.json
PROFILE_MEDIA_DATABASE_V76C_SPEC.md
PROFILE_MEDIA_DATABASE_V76C_GUI_INTEGRATION_NOTES.md
```

## Main GUI changes

`main.py` now creates a main Database workbench card between the progress row
and the text/transcript panels.

The panel displays:

```text
- Database mode status
- case/source/profile counters
- review-lane counters
- planned Database actions
- safety notices
```

V76C also adds the explicit batch JSON import assistant. The GUI selector only
uses files chosen by the user; it does not walk a database folder. The panel is
safe to render even before a real database root or batch JSON file is configured.

## Safety

V76C keeps all established safety invariants:

```text
folder_scan_performed = false
folder_creation_performed = false
folder_move_performed = false
folder_rename_performed = false
file_copy_performed = false
file_write_performed = false
media_download_performed = false
automatic_classification_performed = false
sensitive_identifier_inference_performed = false
```

The GUI panel is a renderer/presenter only. It does not discover files by
walking a database folder, does not mutate folders, and does not infer sensitive
identifiers.

## Stress fixture

`testdata/profile_media_database_v76c_large_gui_stress_fixture.json` provides a larger explicit-batch fixture for main-panel count/render stress testing. It is still just JSON data and performs no filesystem work by itself.
