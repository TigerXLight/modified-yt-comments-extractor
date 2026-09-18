# R43Y Bluesky public appview universal route

R43Y wires the proven Bluesky public appview path into the normal universal social batch/workbench route.

## Result

- Normal Bluesky profile URLs still enter through R43G URL detection.
- R43F still routes through the R43E adapter map first.
- R43E selects the R43W public appview import lane only when `public_network_enabled` and a live/explicit-live mode are present.
- R43W still feeds public `app.bsky.feed.defs#postView` rows into R43V and then R43U.
- R43Y validation uses an injected fake R43W importer, so the patch validation itself does not perform a real network request.

## Boundary

No browser session, WebView2/CefSharp internal copy, cookie/token extraction, login automation, challenge bypass, source-role checks, review-window dependency, or remote media download is introduced.
