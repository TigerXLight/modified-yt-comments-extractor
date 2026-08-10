# MSN Source Adapter Final Lock

This file defines the final non-network lock rule for the MSN source adapter.

The adapter may be considered **structurally locked** when the repository contains the MSN article, comments/profile, offline archive/viewer, media, source-chain, readiness, release, validation, done-gate, acceptance, reconciliation, and closeout modules.

The adapter may be called **complete for a real MSN article** only when an actual operator/manual live result is present and positive. Fixture-only tests are enough for confidence in the architecture, but they are not enough to claim every live MSN page will behave identically.

## Added outputs

`source_msn_adapter_final_lock.py` writes:

- `MSN_SOURCE_ADAPTER_FINAL_LOCK_REPORT.json`
- `MSN_SOURCE_ADAPTER_FINAL_LOCK_REPORT.md`

The report status is one of:

- `COMPLETE`
- `LOCKED_WITH_LIVE_REVIEW`
- `READY_FOR_REAL_ARTICLE_VALIDATION`
- `PARTIAL`
- `BLOCKED`

## Command shape

```cmd
python source_msn_adapter_final_lock.py --target "C:\path\to\MSN output folder" --repo-root "T:\References\to go\Media\tools\Modified YouTube comment extractor"
```

No browser or network action is performed by this command.
