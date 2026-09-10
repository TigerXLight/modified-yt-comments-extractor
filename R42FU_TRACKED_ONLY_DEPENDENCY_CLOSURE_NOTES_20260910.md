# R42FU tracked-only dependency closure

Adds the local Python dependency modules required for a clean tracked-only HEAD import of:

- main.py
- profile_media_source_package_preview.py
- profile_media_database_workbench_panel.py

The dependency closure audit reached IMPORT_OK after copying these candidate modules into a tracked-only git archive temp tree.

No cleanup/delete operation is included.
