# R42GQ YouTube Export Surface App Wiring

Marker: `YTCE_R42GQ_YOUTUBE_EXPORT_SURFACE_APP_WIRING`

Target status: `PASS_R42GQ_YOUTUBE_EXPORT_SURFACE_APP_WIRING`

## Scope

R42GQ wires the R42GP offline YouTube export surface into the evidence/export layer as optional sibling artifacts.

It does not execute YouTube capture, scrape comments, launch a browser/WebView2/CDP session, run screenshots, run yt-dlp, run JDownloader, fetch network resources, harvest account/cookie/token data, bypass CAPTCHA/security, assign source roles, rewrite review windows, mutate counters/no-jump state, or promote metadata-only records.

## Protected Base Output

The existing `comments_readable.txt` output remains the protected Notepad-friendly parent/reply artifact. R42GQ does not rename, remove, or replace it.

The existing screenshots folder remains separate visual evidence. Screenshot files are not required for the text/export-surface helper to run.

## Added Optional Sibling Artifacts

When `include_youtube_searchable_html=True`, the evidence package may receive:

- `youtube-comments-searchable.html`
- `R42GQ_YOUTUBE_EXPORT_SURFACE_WIRING_MANIFEST.json`
- `R42GQ_YOUTUBE_EXPORT_SURFACE_WIRING_REPORT.json`
- `R42GQ_YOUTUBE_EXPORT_SURFACE_WIRING_REPORT.md`
- source-info entries describing the optional surface

When `include_author_profile_urls=True`, the package may also receive:

- `youtube-author-profile-sidecar.json`
- `youtube-author-profile-sidecar.csv`
- `youtube-author-profile-sidecar.html`

`include_author_profile_urls` defaults to `False`, so profile/channel sidecars are not forced into the base export.

## Integration Shape

The standalone helper is:

- `profile_media_youtube_export_surface_app_wiring_r42gq.py`

The tiny additive export hook is:

- `evidence_exporter.create_evidence_package(..., include_youtube_searchable_html=False, include_author_profile_urls=False)`

Both new parameters are default-off and preserve existing behavior unless explicitly enabled.

## Plain URL Policy

Generated manifest/report/sidecar machine fields use plain strings, not Markdown links.

## Verification

The focused test is:

- `profile_media_youtube_export_surface_app_wiring_r42gq_test.py`

It proves:

- R42GP is reachable from the wiring path;
- static/already-captured YouTube comment records can produce sibling artifacts;
- `comments_readable.txt` remains present;
- searchable HTML is additive;
- author profile sidecars are disabled by default;
- enabling `include_author_profile_urls` writes sidecars from existing metadata;
- screenshots remain separate visual evidence;
- no capture/browser/network/download side effects are executed.
