# Profile/Media Database GUI Smoke Checklist V76J

Use a disposable database root first, for example `%TEMP%\ytce_profile_media_manual_gui_smoke`.

1. Start the app and confirm FILES mode remains normal.
2. Turn DATABASE mode on.
3. Confirm the sidebar is only a mode switch and the main Profile/Media Database panel appears.
4. Paste or select an explicit folder-tree text listing; confirm no folder scan happens.
5. Write a standalone batch-preview JSON only after `WRITE_EXISTING_FOLDER_BATCH_PREVIEW`.
6. Load the explicit batch JSON into the main Database workbench.
7. Materialize the selected batch only after `MATERIALIZE_PROFILE_MEDIA_DATABASE_SELECTION`.
8. Apply reviewed folder operations only after `APPLY_PROFILE_MEDIA_REVIEWED_FOLDER_OPERATIONS`.
9. Write the reconciled batch-preview JSON only after `WRITE_RECONCILED_PROFILE_MEDIA_BATCH_PREVIEW`.
10. Refresh the Database panel and verify metrics/review lanes are populated from explicit payloads.

Safety checks: no folder scan, no file copy, no media download, no auto-classification, and no sensitive identifier inference.
