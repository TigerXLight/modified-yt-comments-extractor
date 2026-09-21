# R45AK fail-fast visible-expansion diagnostics

This is a diagnostic runner for the case where R45AJ printed
`R45AK/R45AJ ... AUTO_EXPAND_START` and then immediately reached operator pause
without opening anything.

It keeps the visible-page-only legacy engine, but adds CMD-visible checks:
- `R45AK_PRE_EXPAND_VISIBLE_CONTROL_REPORT`
- `R45AK_FAILFAST_AUTO_EXPAND_DONE`
- `R45AK_AUTO_EXPAND_ZERO_ROUNDS`
- `R45AK_AUTO_EXPAND_FAILED`
- `R45AK_VISIBLE_EXPAND_MISSED_REPORT`

The runner now stops instead of silently continuing to the screenshot pause if the
auto-expander did not actually run.

Safety:
- visible Facebook page expansion only
- no hidden Facebook APIs
- no cookies/tokens/profile parsing
- no WebView2 storage inspection
- no login automation
