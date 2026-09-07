# R42EF bounded debug ZIP64 hotfix

This patch fixes the post-R42EE debug upload builder failure where the matrix succeeded but the upload ZIP never finished.

## Fixes

- Replaces `make_r42ee_bounded_payload_scan_hotfix_debug_upload_zip.py` with a compact upload builder.
- Does not re-run the no-GUI matrix probe.
- Does not print `audit_rows` to the console.
- Uses only bounded latest-output directories.
- Avoids unbounded `profile_media_live_captures` recursion.
- Skips symlinks/reparse-like paths and heavy binary/media/database/build files.
- Opens ZIPs with `allowZip64=True` while still keeping the upload bounded.

## Intended command sequence

```cmd
cd /d "T:\References\to go\Media\tools\Modified YouTube comment extractor" && tools\webview2_source_role_editor_native\smoke_r42ef_bounded_debug_zip64_hotfix.cmd
cd /d "T:\References\to go\Media\tools\Modified YouTube comment extractor" && tools\webview2_source_role_editor_native\make_r42ef_bounded_debug_upload_zip.cmd
```

No archive.ph, GUI, WebView2, Tor/Camoufox, OpenClaw, accounts, credentials, or device capture should run.
