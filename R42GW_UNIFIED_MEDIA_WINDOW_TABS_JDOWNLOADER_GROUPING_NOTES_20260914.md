# R42GW — Unified Media Window Tabs + JDownloader-style Package Grouping

Baseline: `a4aebcc Add Twitter X visible browser media observation store`.

## Decision

The Media surface is one window with three tabs:

- `All`
- `Images`
- `Videos`

The Review window remains separate.

## JDownloader-style source-use policy

R42GW uses JDownloader as an attributed source-reference model. Direct framework, logic, or code adaptation is acceptable when attribution, provenance, and licence compatibility are recorded. The current R42GW patch is still a local Python projection and does not include direct JDownloader source, but that is not a future ban.

The useful Linkgrabber ideas are:

- package/folder parent rows
- child media rows
- variant/manifest/segment children under a video package
- filename, extension, host, type, byte-status, and selectable filters
- segments listed as children, not promoted as top-level spam
- site/file policy controls whether segment children are selectable

## Boundaries

No network actions.
No downloads.
No browser session started.
No hidden X API scraping.
No token/cookie extraction.
No CAPTCHA/challenge bypass.
No source-role assignment.
No review-window rewrite.
No YouTube capture engine changes.
JDownloader source use is not banned; any direct incorporated/adapted source must be attributed, marked, and licence-compatible. Current R42GW direct-source inclusion: false.

## Marker

`YTCE_R42GW_UNIFIED_MEDIA_WINDOW_TABS_JDOWNLOADER_GROUPING`

## Pass

`PASS_R42GW_UNIFIED_MEDIA_WINDOW_TABS_JDOWNLOADER_GROUPING`
