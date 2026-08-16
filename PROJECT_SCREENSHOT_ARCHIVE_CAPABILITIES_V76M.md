# Project Screenshot And Archive Capabilities V76M

Audit date: 2026-08-16

This file separates actual screenshot/archive code from docs, fixtures, and reference-only material.

## Implemented Screenshot Capture

- `IMPLEMENTED`, `TESTED`: `source_local_browser_execution.py` supports local fixture browser execution, rendered DOM snapshot output, full-page screenshot output, selected-element screenshot output when available, deterministic placeholder fallback, progress events, and protected black-frame result modelling.
- `IMPLEMENTED`, `TESTED`: `capture_snapshots.py`, `capture_browser.py`, `capture_page_outline.py`, `capture_article.py`, `capture_comments.py`, and `capture_livechat.py` provide capture contracts and fixture/tested extraction layers.
- `IMPLEMENTED`, `TESTED`: `msn_source_adapter.py` contains callable paths for `capture_msn_android_article_screenshot` and `capture_msn_android_comments_stitched_screenshot`; normal vs debug output names are represented in `production_output_names`.
- `PARTIAL`, `NEEDS_MANUAL_REVIEW`: Real external site screenshot quality depends on current page/runtime behavior and explicit operator-run browser capture. Tests prove code paths and fixtures, not universal live-site success.

## Implemented Rendered DOM / HTML Snapshot

- `IMPLEMENTED`, `TESTED`: `source_msn_live_viewable_capture_cli.py` writes `rendered-page.html`, validation JSON, capture manifest, WARC/WACZ files when requested, and a local viewer.
- `IMPLEMENTED`, `TESTED`: `source_local_webpage_viewer.py` writes an offline `local-viewer-index.html` and open scripts that link to rendered HTML, screenshots, WARC/WACZ, manifests, and validation JSON.
- `IMPLEMENTED`, `TESTED`: `source_replay_static_snapshot.py` writes no-JS static evidence, page, text, TXT, Markdown, and raw WARC outputs.

## WARC / WACZ

- `IMPLEMENTED`, `TESTED`: `capture_warc_wacz.py` provides WARC/WACZ helper functionality.
- `IMPLEMENTED`, `TESTED`: `source_replay_static_snapshot.py` can write static evidence/page/text WARC and WARC.GZ files.
- `IMPLEMENTED`, `TESTED`: `source_local_web_archive_actions.py` and `source_local_web_archive_repair_cli.py` support local archive action/repair flows.
- `IMPLEMENTED`, `NEEDS_MANUAL_REVIEW`: `msn_source_adapter.py` includes offline archive status fields: generated paths, generated booleans, replay-tested booleans, replay status, and limitations.
- `NEEDS_MANUAL_REVIEW`: Generated WARC/WACZ files are not automatically replay-verified unless an explicit replay test result exists. Current reporting should use `NOT_TESTED` when no replay validation ran.

## Archive Provider Clients

- `IMPLEMENTED`, `TESTED`: `source_archive_execution_bridge.py` includes Wayback availability/CDX/submit request builders and archive.today/archive.ph check/submit request builders.
- `IMPLEMENTED`, `TESTED`: Real HTTP execution is injectable through `execute_archive_http_request`; tests use fake clients.
- `IMPLEMENTED`, `TESTED`: ArchiveBox Docker/WSL/remote/native command plans and wrappers exist with timeout/cancel/redaction result handling.
- `NEEDS_MANUAL_REVIEW`: This audit did not contact archive.org, archive.ph, or a real ArchiveBox instance.

## Offline Bundles And Viewers

- `IMPLEMENTED`, `TESTED`: `source_offline_bundle_writer.py` writes compressed evidence bundles containing manifest/provenance/text/HTML/screenshot metadata/comments/media/archive/hash entries where provided.
- `IMPLEMENTED`, `TESTED`: `source_local_webpage_viewer.py` creates an offline review index and CMD launchers.
- `IMPLEMENTED`, `TESTED`: `source_offline_evidence_viewer.py` and related closeout modules provide additional offline evidence viewer support.

## MSN Offline Viewer / Replay Work

- `IMPLEMENTED`, `TESTED`: MSN local viewer, rendered page, static evidence, static page, static text, comments/profile export, and closeout report support exist.
- `IMPLEMENTED`, `NEEDS_MANUAL_REVIEW`: MSN adapter can produce WARC/WACZ artifacts and report their status honestly.
- `NEEDS_MANUAL_REVIEW`: Existing manual history showed WACZ dynamic replay limitations; docs and reports must not claim dynamic ReplayWeb visual success unless a later explicit validation proves it.

## Wayback / Archive.today / ArchiveBox Boundaries

- `IMPLEMENTED`, `TESTED`: Request construction and fake-client tests exist.
- `PARTIAL`, `NEEDS_MANUAL_REVIEW`: Submit operations are approval-gated and not automatically run. Archive.today challenge/manual handoff is modelled; it is not a CAPTCHA bypass.
- `NEEDS_MANUAL_REVIEW`: Real DNS/mirror diagnostics and ArchiveBox runtime depend on local environment/operator approval.

## What Is Reference-Only

- `REFERENCE_ONLY`: external article extraction reference repos are not archive/screenshot code.
- `DOCUMENTED_ONLY`: Some older `SOURCE_ADAPTER_*` Markdown files describe runbooks or acceptance gates without being direct execution code. Treat them as references unless paired with `.py` modules/tests.

