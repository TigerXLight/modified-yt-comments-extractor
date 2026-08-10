# MSN Source Adapter Maintenance Guard

This document locks the maintenance expectations for the MSN source adapter.

The adapter is not allowed to regress in later roadmap work across:

1. Article extraction metadata and body evidence.
2. Comments/profile exports, including nested replies and profile sidecars.
3. Offline webpage viewer and archive labels.
4. Media discovery, media download status, and media hashing when downloaded.
5. Source role / primary source status / source-chain distinction.
6. Readiness, acceptance, certification, and final report generation.
7. Strict live-evidence boundary.

The maintenance guard is conservative: it may report `READY_FOR_LIVE_EVIDENCE`, `RC_LOCKED_PENDING_LIVE_EVIDENCE`, `PROMOTION_BLOCKED`, or `COMPLETE_WITH_POSITIVE_LIVE_EVIDENCE`, but it must not promote the adapter to real-world complete without positive live/manual evidence.
