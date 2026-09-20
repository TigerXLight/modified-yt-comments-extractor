# R45Q Facebook downward frontier expansion repair

R45P could still waste time and leave visible reply controls because it allowed a second global top-to-bottom rescan. R45Q changes the live Facebook expansion strategy to a single downward frontier:

- locally exhaust visible `View hidden replies`, `View all N replies`, `View 1 reply`, and `View more replies` controls before scrolling further down;
- never perform a global scroll-back-to-top rescan;
- keep the old `--progressive-top-down-sweeps` CLI option only as the count of local visible-control exhaustion passes;
- report `downward_only=true`, `global_rescan_used=false`, and `remaining_visible_candidates` in the R45H summary.

This preserves the user's fastest desired workflow: open everything as the pass moves downward instead of jumping back up to catch missed controls.
