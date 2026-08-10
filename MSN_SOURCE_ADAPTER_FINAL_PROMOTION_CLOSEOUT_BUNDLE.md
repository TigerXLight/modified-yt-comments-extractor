# MSN Source Adapter Final Promotion Closeout Bundle

This layer is the final operator-facing bridge between a release-candidate MSN adapter and a genuinely complete MSN adapter.

It does **not** declare MSN complete from no-network fixtures alone. It only promotes the adapter when positive manual/live evidence has been supplied and the required output reports are present.

## Purpose

The MSN adapter has already gained article extraction, comments/profile export, offline viewer/archive support, media registration/download status reporting, readiness gates, final validation, acceptance, closeout, final lock, evidence seal, completion ledger, and release promotion logic.

This bundle adds one final closeout command that can be pointed at an existing MSN output folder and will produce:

- `MSN_SOURCE_ADAPTER_FINAL_PROMOTION_CLOSEOUT.json`
- `MSN_SOURCE_ADAPTER_FINAL_PROMOTION_CLOSEOUT.md`
- `MSN_SOURCE_ADAPTER_FINAL_PROMOTION_CLOSEOUT_CHECKS.csv`

## Decision rule

The final closeout decision is intentionally strict:

- `RC_LOCKED_PENDING_LIVE_EVIDENCE` when no positive manual/live evidence is present.
- `PROMOTION_BLOCKED` when manual/live evidence exists but required checks fail.
- `COMPLETE_WITH_POSITIVE_LIVE_EVIDENCE` only when the operator-supplied live evidence file confirms the required checks and the expected report artifacts are discoverable.

## Required live evidence checks

The live evidence file must confirm these required capabilities:

1. Article extracted.
2. Comments exported.
3. Profiles exported.
4. Offline HTML viewer exists and is usable.
5. Archive output is present and honestly labelled.
6. Media candidates are registered.
7. Media download/status records exist.
8. Source-chain separation is preserved: MSN republisher, visible publisher/source, visible media credit, claimed original source, and source-chain gaps are not collapsed into one false primary source.
9. Final reports exist.
10. No `COMPLETE` claim is made from no-network tests alone.

## Typical workflow

Generate a blank live-evidence template:

```cmd
python source_msn_adapter_live_evidence_template.py --output-dir C:\path\to\msn_output\live_evidence --target-url "https://www.msn.com/..."
```

Fill the template after a real manual/live run, then run:

```cmd
python source_msn_adapter_final_promotion_closeout.py --root C:\path\to\msn_output --out C:\path\to\msn_output\final_promotion_closeout
```

## Output status interpretation

`COMPLETE_WITH_POSITIVE_LIVE_EVIDENCE` is the only status that can be treated as the MSN adapter being done for real-world MSN use. All other statuses mean the adapter remains structurally ready but still pending manual/live confirmation or correction.
