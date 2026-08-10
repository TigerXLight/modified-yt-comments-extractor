# MSN Source Adapter Closeout Orchestrator

This is the final non-network closeout layer for the MSN source adapter work.

The previous MSN adapter modules cover article extraction, comments/profile export, offline viewer/archive status, media registration/download status, readiness gates, final validation, acceptance checks, operator smoke packs, operator final runner, and live-result reconciliation.

This module adds a single closeout command that scans one existing MSN output folder and produces a final, auditable closeout package. It does not scrape live MSN, does not download assets, and does not pretend fixture success equals live success.

## Command

```cmd
python source_msn_adapter_closeout_orchestrator.py --root "C:\path\to\existing\msn-output-folder"
```

Optional output folder:

```cmd
python source_msn_adapter_closeout_orchestrator.py --root "C:\path\to\existing\msn-output-folder" --out "C:\path\to\closeout-reports"
```

Optional manual result:

```cmd
python source_msn_adapter_closeout_orchestrator.py --root "C:\path\to\existing\msn-output-folder" --manual-result "C:\path\to\02_MSN_LIVE_ACCEPTANCE_RESULT_TEMPLATE.json"
```

## Outputs

The command writes:

- `MSN_SOURCE_ADAPTER_CLOSEOUT_REPORT.json`
- `MSN_SOURCE_ADAPTER_CLOSEOUT_REPORT.md`
- `MSN_SOURCE_ADAPTER_CLOSEOUT_CHECKS.csv`
- `MSN_SOURCE_ADAPTER_CLOSEOUT_ACTIONS.md`

## Final states

The closeout state is intentionally conservative:

- `COMPLETE`: static evidence is present and the filled live/manual result says the live target passed.
- `CONFIDENT_WITH_MANUAL_REVIEW`: static evidence is strong, but live/manual result is not filled or is not enough to close live behaviour.
- `PARTIAL`: one or more major areas are partial or incomplete.
- `BLOCKED`: a required area failed or an explicit blocking result is present.
- `INSUFFICIENT_EVIDENCE`: the folder does not contain enough MSN adapter evidence to decide.

## Required evidence areas

The closeout report checks:

1. Article extraction evidence.
2. Comments export evidence.
3. Profile export evidence.
4. Offline HTML viewer evidence.
5. WARC/WACZ evidence with honest partial/experimental labeling.
6. Media inventory and download status evidence.
7. Video/stream candidate status evidence when present.
8. Source-role and primary-source-status fields.
9. MSN republisher / visible publisher / visible media credit / original-source-gap separation.
10. Readiness / release / final validation / done-gate / acceptance / operator-final / reconciliation reports.
11. Filled manual/live acceptance result.

## Important rule

The tool can close the static adapter implementation as confident, but it will not mark live MSN behaviour as complete unless the output folder includes a filled manual/live result showing that the real MSN article target passed.
