# R42EO File Converter Compression UI and Media Windows

Scope: corrective patch after R42EN live testing.

## User-observed issues addressed

- Video & Audio browser grid now exposes the same `Keep original` conversion option already present in the Image browser grid.
- `Add selected to FILES` in browser media grids is neutral by default and turns blue only on hover; `Convert selected` remains the primary/action button.
- Converted outputs are no longer placed into an automatic `Converted:` FILES group. They return to normal FILES root entries unless the user explicitly creates/uses a folder.
- Existing generated conversion groups are flattened/cleared during FILES normalisation so converted files are not trapped in a generated group.
- File Converter held-file display is flattened: master/child fillboxes use bare glyph labels, without per-row card borders around `1.` / `2.` item rows.
- The drop placeholder is only shown when the File Converter is empty. Once held files exist, the placeholder is hidden.
- Held rows use more horizontal space and keep conversion controls on the right to reduce clipping on resize.
- The replacement Icons8 K icon is used where available, with fallback to the older Kappa icon.
- Each held row has a per-file C/compression toggle next to the K/keep-original toggle.
- K and C toggles update in place and do not rebuild/refresh the held list.

## Compression design boundary

R42EO adds a local desktop compression path to the existing converter backend. The downloaded JavaScript/browser projects are reference sources for logic and settings, not embedded runtime dependencies in this patch.

- Image compression starts with getButterfly-style simple settings: quality percentage, max side, and output suffix.
- Video compression starts with native local FFmpeg options: CRF, optional max side scaling, and conservative audio bitrate handling.
- Audio compression starts with native local FFmpeg bitrate presets.
- Text compression is intentionally deferred because real text compression means archive formats such as `.zip` / `.gz`, not editable text conversion.

## Safety boundary

The File Converter remains local-only: no browser, WebView2, archive.ph, account, or network action is introduced by conversion planning/execution.
