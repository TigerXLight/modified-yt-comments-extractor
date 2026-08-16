# Profile/Media Database V76F — Controlled Materialize Pack

V76F adds a controlled materialization workflow for the Profile/Media Database.
It turns explicit batch JSON selections into real case folders and metadata
records only after an exact top-level confirmation phrase is supplied.

## Confirmation phrase

`MATERIALIZE_PROFILE_MEDIA_DATABASE_SELECTION`

The V76F confirmation gates the whole selected batch set.  Once it is valid,
the workflow delegates to the existing guarded V75V/V75U batch/materialize
confirmations internally.

## What it may do after confirmation

- create the known Database/Profile/Case folders already planned by V75Q/V75U
- write JSON/TXT source-claim, profile-record, and case-manifest files
- preserve V76E canonical source-role normalization, including the legacy alias
  `SECONDARY_WITNESS_SOURCE` becoming `SECONDARY_WITNESS_ACCOUNT`

## What it still must not do

- no folder scan
- no folder move
- no folder rename
- no file/media copy
- no media download
- no automatic classification
- no sensitive-identifier inference
- no mutation from an existing folder import preview unless the preview has first
  been written as explicit batch JSON and then selected by the V76C/V76D loader

## Added files

- `profile_media_database_materialize_workflow.py`
- `profile_media_database_materialize_workflow_test.py`
- `profile_media_database_materialize_gui_adapter.py`
- `profile_media_database_materialize_gui_adapter_test.py`
- `tools/run_profile_media_database_materialize_cli_v76f.py`
- `testdata/profile_media_database_v76f_materialize_fixture.json`
- `testdata/profile_media_database_v76f_large_materialize_fixture.json`
- `PROFILE_MEDIA_DATABASE_V76F_SPEC.md`
- `PROFILE_MEDIA_DATABASE_V76F_MATERIALIZE_NOTES.md`

## Updated files

- `main.py`
- `profile_media_database_workbench_panel.py`
- `profile_media_database_gui_panel_main_test.py`
