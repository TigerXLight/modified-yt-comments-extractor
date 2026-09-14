# R42GR YouTube Export Surface UI Options / App Plumbing

Status target: `PASS_R42GR_YOUTUBE_EXPORT_SURFACE_UI_OPTIONS_APP_PLUMBING`

R42GR exposes the R42GQ optional YouTube export-surface booleans through the
existing app/export path without changing capture engines:

- `include_youtube_searchable_html`
- `include_author_profile_urls`

The combined YouTube settings window now shows:

- `Create searchable comments HTML`
- `Include author channel/profile URL sidecars`

Both options default to `False`. The existing readable
`comments_readable.txt` output remains the protected base artifact. Searchable
HTML and author profile/channel sidecars are sibling artifacts only. Screenshot
evidence remains separate and is not required for text export.

Implementation boundaries:

- no live YouTube capture;
- no comment scraping;
- no browser/WebView2/CDP launch;
- no screenshot run;
- no network fetch;
- no media download;
- no yt-dlp or JDownloader execution;
- no source-role assignment;
- no review-window rewrite;
- no counter/no-jump mutation;
- no metadata-only promotion.

The helper module `profile_media_youtube_export_surface_ui_options_r42gr.py`
provides the options model, app variable collector, deterministic offline report
generation, and CLI marker/report. `main.py` only creates defaults-off variables,
renders two checkboxes in the existing YouTube settings dialog, records the two
plain option names in the export settings dict, and passes the booleans to
`evidence_exporter.create_evidence_package(...)`.
