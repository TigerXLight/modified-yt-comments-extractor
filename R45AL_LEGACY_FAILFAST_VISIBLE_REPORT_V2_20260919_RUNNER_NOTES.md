# R45AL fail-fast visible report v2

R45AK correctly failed instead of silently continuing, but it exposed two bugs:

1. `R45AK_VISIBLE_EXPAND_PREFLIGHT_JS` was referenced but not actually defined
   in the generated J runner.
2. The bounded auto-expand JS called `norm(text)` inside
   `isReportableExpandLabel`, but no `norm` helper existed in that JS scope.

R45AL fixes both while keeping the visible-page-only legacy runner approach.

Expected live markers:
- `R45AL_PRE_EXPAND_VISIBLE_CONTROL_REPORT`
- `R45AL_FAILFAST_V2_AUTO_EXPAND_START`
- `R45H_PROGRESS ...`
- `R45AL_FAILFAST_V2_AUTO_EXPAND_DONE`
- `R45AL_VISIBLE_EXPAND_MISSED_REPORT`

Safety:
- visible Facebook page expansion only
- no hidden Facebook APIs
- no cookies/tokens/profile parsing
- no WebView2 storage inspection
- no login automation
