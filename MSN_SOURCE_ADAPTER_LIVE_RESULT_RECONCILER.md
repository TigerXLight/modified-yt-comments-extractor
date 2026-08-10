# MSN Source Adapter Live Result Reconciler

This module is the final evidence-facing reconciliation step for the MSN source adapter.

It does not scrape live pages, download network assets, or claim live success by inference. It reads an existing MSN output folder and combines:

- static adapter outputs,
- final validation reports,
- done-gate / acceptance reports,
- operator smoke/live acceptance outputs,
- manual result templates filled by the operator,
- media/source-chain sidecars where present.

The output is an explicit final release decision:

- `COMPLETE`
- `CONFIDENT_WITH_MANUAL_REVIEW`
- `PARTIAL`
- `BLOCKED`
- `INSUFFICIENT_EVIDENCE`

The intent is to prevent a false claim that MSN is complete merely because offline fixtures passed.

## CLI

```cmd
python source_msn_adapter_live_result_reconciler.py --root "C:\path\to\msn-output-folder"
```

Optional output directory:

```cmd
python source_msn_adapter_live_result_reconciler.py --root "C:\path\to\msn-output-folder" --out "C:\path\to\reports"
```

The CLI writes:

- `MSN_SOURCE_ADAPTER_LIVE_RECONCILIATION_REPORT.json`
- `MSN_SOURCE_ADAPTER_LIVE_RECONCILIATION_REPORT.md`

## What it checks

The reconciler checks for evidence of:

1. Article extraction outputs.
2. Comments and profile exports.
3. Offline viewer / rendered HTML / WARC / WACZ outputs.
4. Media inventory and media download status sidecars.
5. Video/stream candidate status where present.
6. MSN republisher / visible publisher / original source gap distinction.
7. Source-role and primary-source-status fields.
8. Final validator, done-gate, acceptance-suite, and operator-final reports.
9. Manual live acceptance result intake.
10. Any contradictory fail/blocked/partial findings.

## Important limitation

The reconciler is a decision engine, not a browser automation layer. It can honestly mark the adapter as complete only when the provided output folder contains both static reports and a manual/live result indicating the live article passed.

Without a filled live result, the strongest status it should emit is normally `CONFIDENT_WITH_MANUAL_REVIEW`.
