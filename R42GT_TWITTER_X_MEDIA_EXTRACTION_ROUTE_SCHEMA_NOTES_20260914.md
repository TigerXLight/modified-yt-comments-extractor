# R42GT Twitter/X Media Extraction Route Schema Notes

Status target: `PASS_R42GT_TWITTER_X_MEDIA_EXTRACTION_ROUTE_SCHEMA`

R42GT adds an offline app-side schema and package writer for Twitter/X media evidence bundles. It registers the route and writes deterministic package/index/report artifacts from supplied records or local fixture files only.

Boundaries preserved:

- No live X/Twitter capture.
- No browser, WebView2, CDP, or network capture.
- No login automation, token/cookie access, or challenge bypass.
- No media download from X.
- No source-role assignment, review-window rewrite, counter/no-jump mutation, or metadata promotion.
- Remote media candidates remain metadata-only/review-required unless a local fixture file already exists.

The package writer creates `source_exports/twitter_x/<account>/capture_<timestamp>/` with manifest, media indexes, timeline files, review strings, source info, and per-post `post.json` / `post.md` / `media/` folders. Local fixture media is copied and hashed; remote candidate URLs are recorded as plain URL metadata only.
