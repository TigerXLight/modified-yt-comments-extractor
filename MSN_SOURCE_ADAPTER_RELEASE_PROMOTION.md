# MSN Source Adapter Release Promotion

The release promotion gate is the final decision layer for the MSN adapter.

It reads:

- filled manual/live evidence, through `source_msn_adapter_live_evidence_validator.py`
- no-network output reports already produced by the adapter toolchain
- final validation / acceptance / done-gate / closeout / final-lock outputs when present

It writes:

- `MSN_SOURCE_ADAPTER_RELEASE_PROMOTION_REPORT.json`
- `MSN_SOURCE_ADAPTER_RELEASE_PROMOTION_REPORT.md`

Possible promotion states:

- `COMPLETE`: positive manual/live evidence exists and no failing no-network report was found.
- `RC_LOCKED_PENDING_LIVE_EVIDENCE`: no manual/live evidence exists yet.
- `PARTIAL`: manual/live evidence exists but required live checks are incomplete or rejected.
- `BLOCKED`: a no-network report is failing/blocking and must be fixed before promotion.
- `INSUFFICIENT_EVIDENCE`: the target folder cannot be evaluated.

This keeps the MSN goal honest. The code may be architecturally complete, but a live-MSN COMPLETE claim requires positive filled operator evidence.

Example:

```cmd
C:\Users\fahad\AppData\Local\Programs\Python\Python311\python.exe source_msn_adapter_release_promotion.py --root "C:\path\to\msn_output_folder"
```
