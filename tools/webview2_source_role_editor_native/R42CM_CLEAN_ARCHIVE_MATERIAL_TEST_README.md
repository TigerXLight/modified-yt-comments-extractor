# R42CM hard-clean archive material test kit

This replaces the broken R42CL verifier. R42CL failed because the batch file used a Unix-style `<<PY` heredoc inside Windows CMD.

Run order:

1. `tools\webview2_source_role_editor_native\prepare_r42cm_hard_clean_archive_material_test.cmd`
2. If prepare prints any `FAIL`, stop and fix that first. Do not continue with a contaminated test.
3. `tools\webview2_source_role_editor_native\build_r42ai_native_source_role_editor.cmd`
4. `C:\Users\fahad\AppData\Local\Programs\Python\Python311\python.exe main.py`
5. Input the three-link TXT and let the app process it.
6. Close the app after the Review DB window stops changing for a couple of minutes.
7. `tools\webview2_source_role_editor_native\verify_r42cm_archive_material_test.cmd`
8. Upload the audit text plus normal R42CK debug ZIP.

The hard-clean prepare script kills `msedgewebview2.exe`, moves the WebView2 UDF, moves the source-role overlay folder, and moves old test-article capture folders matching archive.ph/Metro/Wayback so old cached text cannot masquerade as a fresh archive.ph material capture.
