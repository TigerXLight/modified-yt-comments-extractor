# Screenshot Archive Reference Coverage V76N

Audit date: 2026-08-16

This file compares screenshot/page/archive references against actual app code.

## Reference Set

| Reference | Type | App coverage | Status |
| --- | --- | --- | --- |
| GoFullPage extension archive | browser extension full-page screenshots | app-owned browser/screenshot modules | `REFERENCE_ONLY`, `PARTIAL`, `SUPERSEDED` |
| PageCap extension archive | browser extension page capture | app-owned browser/screenshot modules | `REFERENCE_ONLY`, `PARTIAL` |
| `mrcoles__full-page-screen-capture-chrome-extension` | full-page screenshot extension | `capture_browser.py`, `source_local_browser_execution.py` | `REFERENCE_ONLY`, `PARTIAL` |
| `kubahorak__pagecap` | page capture reference | app local capture and static replay | `REFERENCE_ONLY`, `PARTIAL` |
| `stratofax__pagecap` | page capture reference | app local capture and static replay | `REFERENCE_ONLY`, `PARTIAL` |
| `EverythingSuckz__webshot-api` | web screenshot API | no service equivalent | `REFERENCE_ONLY`, `NOT_IMPLEMENTED` |
| `sea-deep__link-to-screenshot` | URL screenshot service | no service equivalent | `REFERENCE_ONLY`, `NOT_IMPLEMENTED` |
| `kdippan__SnapStream` | screenshot app/API | no Microlink/API integration | `REFERENCE_ONLY`, `NOT_IMPLEMENTED` |
| `copperline-labs__rendex-mcp` | render/capture MCP | no MCP integration | `REFERENCE_ONLY`, `NOT_IMPLEMENTED` |
| `myselfshravan__third-eye` | browser/screenshot reference | local capture modules only | `REFERENCE_ONLY`, `PARTIAL` |
| `carbogninalberto__fast-html-to-pdf-api` | HTML-to-PDF capture | no PDF capture service | `REFERENCE_ONLY`, `NOT_IMPLEMENTED` |

## Current App Capabilities

| Capability | Status | Files/tests | Notes |
| --- | --- | --- | --- |
| Normal screenshot capture | `IMPLEMENTED`, `TESTED` | `capture_browser.py`, `capture_snapshots.py`, tests | Browser request/result and screenshot artifact models exist. |
| Full-page screenshot capture | `IMPLEMENTED`, `TESTED` | `capture_browser.py` (`screenshot_full_page`), `source_local_browser_execution.py` | Tests are fixture/local; not universal live-site proof. |
| Rendered DOM capture | `IMPLEMENTED`, `TESTED` | `source_local_browser_execution.py`, `source_msn_live_viewable_capture_cli.py` | Writes rendered DOM/HTML artifacts in controlled paths. |
| Scroll capture | `PARTIAL`, `TESTED` | `msn_source_adapter.py` V15 internal scroller stitching; capture scroll runtime docs/modules | Site-specific logic exists; generic scroll-capture parity with extensions is not complete. |
| Page save/offline viewer | `IMPLEMENTED`, `TESTED` | `source_local_webpage_viewer.py`, `source_replay_static_snapshot.py` | Direct HTML/local viewer/static page/text outputs exist. |
| Archive manifest | `IMPLEMENTED`, `TESTED` | `capture_warc_wacz.py`, `source_local_web_archive_actions.py`, `total_export_manifest.py` | Manifest and archive metadata are separated from visual replay success. |
| WARC support | `IMPLEMENTED`, `TESTED` | `capture_warc_wacz.py`, `source_replay_static_snapshot.py`, `source_local_web_archive_actions.py` | Static/raw WARC writers and repair helpers exist. |
| HAR support | `PARTIAL`, `TESTED` | Twitter HAR/timeline parsing modules | HAR is present mainly in Twitter capture/cursor tooling, not as a universal archive format. |
| MSN offline viewer/replay | `IMPLEMENTED`, `TESTED`, `NEEDS_MANUAL_REVIEW` | `source_local_webpage_viewer.py`, `source_replay_static_snapshot.py`, `source_msn_live_viewable_capture_cli.py`, `msn_source_adapter.py` | Dynamic ReplayWeb/WACZ success is not inferred from generated artifacts. |
| Wayback/archive.today request builders | `IMPLEMENTED`, `TESTED` | `source_archive_execution_bridge.py`, `capture_archive_wayback.py`, `capture_archive_today.py` | Fake-client tested; no live archive calls in this audit. |
| ArchiveBox execution wrapper | `IMPLEMENTED`, `TESTED`, `NEEDS_MANUAL_REVIEW` | `source_archive_execution_bridge.py`, `capture_archivebox.py` | Real Docker/WSL/ArchiveBox run requires explicit approval/environment. |

## Exact Missing Pieces

- `NOT_IMPLEMENTED`: Chrome extension UI/parity for GoFullPage/PageCap/full-page-screen-capture is not copied and should not be vendored.
- `NOT_IMPLEMENTED`: webshot/link-to-screenshot public API service integration is not implemented.
- `PARTIAL`: generic scroll-stitch capture is not as broad as all screenshot extension references; MSN V15 internal-scroller stitching is site-specific.
- `PARTIAL`: HAR capture is not a universal page-archive path; it is mostly tied to Twitter/X browser capture/cursor tooling.
- `NEEDS_MANUAL_REVIEW`: WARC/WACZ replay verification remains distinct from WARC/WACZ generation.

## Safety Notes

- `DO_NOT_VENDOR`: browser extension/reference source code should not be copied wholesale.
- `NEEDS_MANUAL_REVIEW`: browser capture against external sites can expose access patterns and must be operator-gated.
- `DO_NOT_IMPLEMENT_WRITE_ACTION`: archive submit remains explicit/approval-only; archive checks and local repairs are separate from submit.

