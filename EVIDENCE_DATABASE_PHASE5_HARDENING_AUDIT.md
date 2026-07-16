# Evidence Database Phase 5 Hardening Audit

Date: 2026-07-16

Checkpoint: `be81a53 Document evidence database demo import export support`

## Scope

Evidence Database Phase 5 hardens the existing review, synthetic fixture,
standalone scaffold, and JSON import/export layers with regression tests and
small defensive fixes only.

This phase remains local, fixture-oriented, review-only, dry-run-only, and
explicit-record-only. It does not approve broad user-folder scanning, real
evidence file movement, automatic classification execution, live site capture,
archive/provider calls, downloads, scraping, browser automation, credential
access, provider/network behavior, sensitive-attribute inference, or `main.py`
layout changes.

## Edge Cases Covered In This Phase

- Import/export tampering and compatibility:
  - schema version mismatch;
  - missing payload hash;
  - incorrect payload hash;
  - extra unknown top-level fields;
  - malformed record payload;
  - destructive-looking apply-plan flags;
  - secret-like keys nested inside imported payloads.
- Synthetic fixture and scaffold review states:
  - empty demo/review session summaries;
  - duplicate record ID preview behavior;
  - missing root metadata;
  - all classification groups empty except one;
  - rejected and superseded decisions visible in summaries;
  - dry-run warnings always rendered.
- Existing workflow guardrails:
  - no visible Evidence Database hook added to `main.py`;
  - sidebar order remains `UPDATES`, `KEYS/ACCOUNTS`, `EXPORT`, `FILES`;
  - source-resource, Total Export manifest, and session FILES tests continue
    to pass.

## Still Deferred

- Real evidence database root scanning.
- Real user-folder indexing or migration.
- Classification execution or automatic reclassification.
- Evidence file movement, copying, renaming, or deletion.
- Visible `main.py` placement for the standalone review scaffold.
- Live website capture, archive checks/submission, downloads, scraping,
  browser automation, provider/network behavior, credential access, or
  sensitive-attribute inference.
