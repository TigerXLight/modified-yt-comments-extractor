# R45BI fix: robust expected-total progress gate

R45BH failed on an outdated text anchor (`expected_total_comments init`) after the R45BG no-hover patch changed the runner shape. R45BI re-applies the intended feature with current R45BG-compatible anchors.

Changes:
- adds `--expected-total-comments`;
- for this post, run with `--expected-total-comments 715`;
- ignores unrelated progress counters whose total is not 715, e.g. `20 of 100`;
- logs `R45AX_PROGRESS_IGNORED_EXPECTED_TOTAL_MISMATCH` for ignored counters;
- completion requires the filtered progress gate to reach the expected total;
- preserves R45BG mouse parking, R45BE target-drift guard, R45BD Messenger guard, R45BC dead-click skip, R45BB full audit restarts, and R45BA real-scroller selection.

Visible-page only. No hidden Facebook APIs, no cookies/tokens, and no browser-profile parsing/copying.
