# REV4 manual live site-smoke approval packet

This document records the local-only boundary for preparing a manual live site-smoke approval packet.

## Purpose

The approval packet is a metadata-only checklist for named sites and named operator actions. It does not run live site capture, browser automation, screenshots, archive submission, media download, WARC/WACZ capture, ArchiveBox, provider calls, credential reads, file movement, or user-folder scanning.

## Added local modules

- `capture_manual_live_smoke_approval_packet.py`
- `capture_manual_live_smoke_approval_packet_store.py`
- `capture_manual_live_smoke_approval_packet_store_cli.py`
- `capture_manual_live_smoke_approval_packet_verifier.py`
- `capture_manual_live_smoke_approval_section_closeout.py`

## Safety invariants

- `review_status` remains `APPROVAL_REQUIRED` or `USER_REVIEW_REQUIRED`.
- `execution_mode` remains `MANUAL_OPERATOR_ONLY`.
- Runtime execution flags remain false.
- Live network, browser, screenshot, archive, media, WARC/WACZ, ArchiveBox, credential, raw-media, full-path, file-movement, and completed/verified-capture flags remain false.
- Stored outputs return safe filenames, hashes, byte counts, and schema versions only.

## Operational boundary

This is not approval to execute a live smoke test. A separate user approval must still name the site, operator action, output directory, and manual capture/archive behavior before any live or manual site action is performed.
