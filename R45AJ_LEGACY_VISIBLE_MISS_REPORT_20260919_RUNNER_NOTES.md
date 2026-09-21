# R45AJ legacy visible missed-expansion reporter

This is a separate runner built from R45AI.

Why:
- The live R45AI CMD showed very large `candidate_count` values while only a small
  number of controls were clicked in each round.
- That meant offscreen candidates could consume the batch before the currently
  visible "View all N replies" / "View hidden replies" controls were reached.
- The screenshot then showed visible controls still missed.

Fix:
- Filter candidates to currently visible controls before slicing the batch.
- Keep clicking visible controls only.
- Keep the older working 2026-09-19 legacy page-side click engine.
- Print remaining visible missed expansion controls to CMD as:
  `R45AJ_VISIBLE_EXPAND_MISSED_REPORT {...}`.
- Each `R45H_PROGRESS` row also includes:
  `visible_candidate_count`,
  `remaining_visible_expand_count`,
  `remaining_visible_expand_labels`.

Interpretation:
- `PASS_NO_VISIBLE_EXPAND_CONTROLS` = no visible reply/hidden/comment expansion controls were found at the end.
- `NEEDS_MORE_EXPANSION` = at least one visible reply/hidden/comment expansion control remained and is listed in CMD.

Safety:
- visible Facebook page expansion only
- no hidden Facebook APIs
- no cookies/tokens/profile parsing
- no WebView2 storage inspection
- no login automation
