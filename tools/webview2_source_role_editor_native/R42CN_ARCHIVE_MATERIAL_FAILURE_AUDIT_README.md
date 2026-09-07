# R42CN archive material failure audit

This is a diagnostic/test-kit patch, not an app behaviour patch.

It fixes the R42CM verifier BOM crash by reading JSON with `utf-8-sig`, then audits the clean archive.ph material test for:

- whether the alternate clean WebView2 UDF was used;
- whether current source-role overlay/roleplan files exist;
- whether fresh post-marker files contain `archive.ph/6Mr3C` and article text;
- whether fresh `r40d_external_live_article` archive.ph capture folders exist;
- whether `browser_capture_failed` / Playwright failure lines appear;
- whether current SQLite roleplan rows exist for archive/title terms.

Run after the failed test:

```cmd
cd /d "T:\References\to go\Media\tools\Modified YouTube comment extractor" && powershell -NoProfile -ExecutionPolicy Bypass -Command "$env:LOCALAPPDATA='T:\References\to go\Media\tools\Modified YouTube comment extractor\profile_media_live_captures\r42cm_alt_clean_localappdata'; & 'tools\webview2_source_role_editor_native\verify_r42cn_archive_material_failure_audit.cmd'; exit $LASTEXITCODE"
```

Upload the TXT and ZIP written to Downloads.
