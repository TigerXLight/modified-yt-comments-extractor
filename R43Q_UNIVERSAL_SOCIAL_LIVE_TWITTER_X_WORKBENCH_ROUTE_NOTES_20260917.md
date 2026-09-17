# R43Q Universal Social Live Twitter/X Workbench Route Notes

Marker: `YTCE_R43Q_UNIVERSAL_SOCIAL_LIVE_TWITTER_X_WORKBENCH_ROUTE`

R43Q routes explicit live Twitter/X workbench runs through the existing universal chain:

`R43L -> R43J -> R43I -> R43H -> R43G -> R43F -> R43E -> R43D`

The patch does not add a parallel control plane. R43L/R43J/R43I still delegate through the universal workbench, queue, intake, export surface, and adapter map. The Twitter/X adapter boundary at R43D is the only place that invokes the proven R43N/R43O/R43P live evidence path.

## Live Option Propagation

The request stack now carries these backward-compatible fields with safe defaults:

- `explicit_live_mode`
- `run_visible_live`
- `live_mode`
- `browser_user_data_dir`
- `browser_executable_path`
- `max_items`
- `max_scrolls`

R43H persists the live options onto queue records so run/resume/retry delegate queues cannot silently drop the explicit live intent.

## Adapter Boundary

When explicit live mode is requested and fixture mode is false, R43D delegates to R43N. R43N then uses R43O/R43P for visible-session binding and runner-output promotion. R43D translates the R43N observation receipt into `live_evidence_summary` and promoted post/media/screenshot counts.

The safe/default route remains unchanged when no live option is supplied.

## Fake PASS Guard

R43D only returns its normal PASS status for explicit live mode when R43N returns a PASS status and promoted non-fixture post/media/screenshot evidence is present. Network-only evidence remains blocked.

## App-Shell Receipt

R43L now writes `live_evidence_summary` to `app_shell_receipt.json`, including:

- R43N/R43O/R43P statuses
- promoted post/media/screenshot counts
- promoted network/API/response-body counts
- promoted observation paths
- blocker reason when blocked

This lets the normal workbench/app-shell receipt prove whether the live path passed or truthfully blocked without manual nested-receipt spelunking.
