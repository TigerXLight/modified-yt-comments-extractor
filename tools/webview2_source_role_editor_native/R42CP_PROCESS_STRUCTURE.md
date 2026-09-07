# R42CP archive material interaction bridge

R42CP extends R42CO by wiring the app-owned native WebView2 session into the production `GO -> Webpage -> source material` path.

Expected archive source route:

1. Source URL row is archive.ph/archive.today/archive.is/etc.
2. `GO` with Webpage enabled calls the archive material chain before generic Playwright.
3. Direct archive HTTP mirrors are attempted only as a quick first probe.
4. The native WebView2 warm server receives `action=material_capture`.
5. The visible/app-owned WebView2 session navigates to the submitted archive URL.
6. The helper repeatedly extracts rendered DOM/body text until article material is found or timeout occurs.
7. On success it writes `article_text.txt`, `archive_page.html`, and `native_webview2_material_capture.json` inside the archive material folder.
8. The source row can then continue through FILES/source-role judgement from fresh source 03 material.

This patch does not treat old Metro/Wayback text, dropdown presence, or direct HTTP 429 pages as success.
