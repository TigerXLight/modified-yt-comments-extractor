# MSN Source Adapter Total Package

This module is the adapter-level bridge for existing MSN capture/export folders. It does not run live capture by itself. It joins the artifacts already produced by the MSN workflow into one reviewable source-evidence package.

## Inputs

- Rendered article HTML, normally `rendered-page.html`.
- Offline archive/viewer files, normally `rendered-page.warc.gz`, strict WACZ, validation metadata, capture manifest, and `local_viewer/open_local_viewer.cmd`.
- Comments/profile exports, normally the V35-style comments/profile JSON plus TXT/MD/HTML/profile files when available.
- Media discovery/download sidecars, normally `msn-media-download-results.json` when media has been explicitly selected and captured.
- Optional request-log JSON for video/stream/media candidates that only appear in browser/network observation.

## Outputs

- `MSN_SOURCE_ADAPTER_BUNDLE.json`
- `MSN_SOURCE_ADAPTER_READINESS.json`
- `msn-source-adapter-release-report.json`
- `msn-source-adapter-release-report.md`
- `msn-source-adapter-release-manual-live-validation.md`
- `MSN_ADAPTER_FINAL_VALIDATION_REPORT.json`
- `MSN_ADAPTER_FINAL_VALIDATION_REPORT.md`
- `MSN_SOURCE_ADAPTER_TOTAL_PACKAGE_SUMMARY.json`
- `MSN_SOURCE_ADAPTER_TOTAL_PACKAGE_INDEX.md`

## Source-role rule

The total package preserves the project evidence hierarchy. MSN is the captured platform/republishing surface. A publisher such as The Independent is preserved as the visible publisher/source. A visible image/video credit such as Google Street View is preserved as a media-credit/source-chain clue. None of those are silently promoted to the original primary authored source unless the original source is actually located.

## Manual review rule

This package can make the MSN adapter structurally confident. It does not remove manual review. ReplayWeb/WACZ behaviour, live MSN comments, changing shadow DOM, video delivery, and original media source-chain claims remain manually validated.
