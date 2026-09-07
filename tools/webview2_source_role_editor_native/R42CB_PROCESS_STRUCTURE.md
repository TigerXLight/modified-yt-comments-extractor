# R42CB Native WebView2 source-role editor patch

R42CB is based on the working R42BZ code path and keeps the true native toolbar above the WebView2 rectangle.

Changes in R42CB:

- Source selector now shows source-title labels instead of `1/2 Original` labels.
- Original format: `Article title | Site`.
- Wayback format: italic/bold `W | Article title | Site`.
- Archive.ph/archive.today/etc. format: italic/bold `A | Article title | Site`.
- The source selector draws title and site separately so the site suffix remains visible while the title ellipsizes.
- Full current URL is kept in the native window title and URL tooltip.
- Semantic/Media buttons are owner-drawn rounded buttons to avoid the odd WinForms outline/focus rectangle.
- Icon buttons suppress focus-cue drawing and keep the real project PNG icons owner-drawn.
- Keeps R42BZ direct native toolbar mode bridge, so Semantic/Media clicks repaint the WebView and update counters.
