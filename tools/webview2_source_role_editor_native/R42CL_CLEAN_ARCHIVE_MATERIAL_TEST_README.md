# R42CL clean archive material test kit

Purpose: create a clean, non-contaminated test for whether `https://archive.ph/6mr3C` obtains fresh page material and a source-role result as its own source candidate.

This test backs up and moves aside:

- `profile_media_live_captures\link_source_role_webview_overlay`
- `%LOCALAPPDATA%\YTCE\WebView2SourceRoleEditor`

It does not delete them; they are moved into `profile_media_live_captures\r42cl_clean_archive_material_test_backups\...`.

Run order:

1. `tools\webview2_source_role_editor_native\prepare_r42cl_clean_archive_material_test.cmd`
2. `tools\webview2_source_role_editor_native\build_r42ai_native_source_role_editor.cmd`
3. `C:\Users\fahad\AppData\Local\Programs\Python\Python311\python.exe main.py`
4. Input the 3-link TXT and let the app process it without using the edit window as the worker.
5. `tools\webview2_source_role_editor_native\verify_r42cl_archive_material_test.cmd`
6. Upload the generated audit TXT and the normal debug ZIP.

Pass signal:

- Recent post-start files contain `https://archive.ph/6mr3C` and article text/material.
- SQLite has current `role_plan_rows` / `role_plan_current` for selected URL `https://archive.ph/6mr3C`, not just old inherited Metro rows.

Fail signal:

- No recent archive material files are created.
- The only archive.ph rows are old copied rows.
- Source 03 is present visually but role/source rows come from duplicate/inherited old content.
