# MSN Source Adapter Live Run Binder

This document defines the final operator-facing binder for an MSN source-adapter run.

The binder is not a scraper. It is the final packaging surface used after an MSN output folder already exists. It collects the generated MSN reports, live-evidence result, archive/media manifests, and source-chain checks into one folder so later work can prove what was validated.

## Locked rule

No tool in this layer may label a real MSN adapter run as `COMPLETE` unless there is positive manual/live evidence. No-network self-tests can only prove that the validator logic works.

## Binder states

- `BINDER_PENDING_LIVE_EVIDENCE`: the folder is structurally ready, but no positive live result was found.
- `BINDER_BLOCKED`: the live evidence file is present but records a failed or blocked area.
- `BINDER_COMPLETE_WITH_POSITIVE_LIVE_EVIDENCE`: a positive live result exists and all required live checks are marked pass/yes/true/ok.

## Required live checks

The binder expects evidence for these areas:

1. article extraction
2. comments extraction
3. profile export
4. offline viewer
5. WARC or archive evidence
6. media discovery / media status
7. source-chain / source-role preservation

The binder intentionally separates MSN as captured surface, visible publisher/source credit, media credit, and original-source status.
