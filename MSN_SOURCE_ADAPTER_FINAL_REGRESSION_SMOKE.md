# MSN Source Adapter Final Regression Smoke

This file records the intended usage of the final regression-smoke layer.

Use this when any later roadmap patch touches source evidence, total export, media capture, browser capture, preservation, or GUI wiring.

Minimum operator flow:

1. Run the regression smoke runner in execute mode.
2. Run the live-validation index against a known MSN output folder.
3. Confirm that status wording has not drifted away from:
   - `READY_FOR_LIVE_EVIDENCE`
   - `RC_LOCKED_PENDING_LIVE_EVIDENCE`
   - `PROMOTION_BLOCKED`
   - `COMPLETE_WITH_POSITIVE_LIVE_EVIDENCE`
4. Do not claim final live MSN completion unless the live-evidence file exists and is positive.

This file exists so later sessions preserve the MSN adapter standard and do not reduce it to a generic downloader or a flat webpage scraper.
