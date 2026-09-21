# R45AP simple ordered exhaust engine

R45AP is a reset/simplification after the legacy/R45AO path kept detecting
leftover controls but not actually exhausting them.

Core rule:

1. Click the first/topmost visible expansion control.
2. Rescan the same viewport.
3. Do not scroll while visible expansion controls remain.
4. Only scroll when the current viewport has zero pending controls.
5. At bottom / after no visible controls, count all loaded controls.
6. If all-loaded count is non-zero, scroll directly to the first remaining loaded control.
7. Repeat until all-loaded count is zero.
8. If the count stops reducing, print `R45AP_BLOCKED_REMAINING_EXPAND_CONTROLS`
   and exit non-zero. No final screenshot should be accepted while controls remain.

Visible-page-only safety:
- no hidden Facebook APIs
- no Graph endpoints
- no cookies/tokens/profile parsing
- no WebView2 storage inspection
- no login automation

Expected live markers:
- `R45AP_SIMPLE_ORDERED_EXHAUST_START`
- `R45AP_VISIBLE_PENDING`
- `R45AP_CLICK`
- `R45AP_ALL_LOADED_PENDING`
- `R45AP_SCROLL_TO_FIRST_REMAINING`
- `R45AP_COMPLETE`
- `R45AP_FINAL_ALL_LOADED_MISSED_REPORT`
