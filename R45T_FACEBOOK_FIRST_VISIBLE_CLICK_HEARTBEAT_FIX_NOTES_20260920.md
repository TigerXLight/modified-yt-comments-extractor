# R45T Facebook first-visible click heartbeat and stronger visible click fix

Purpose: keep the operator-requested fastest downward strategy, but make it observable and avoid silent local loops.

Rules implemented:

- Strict downward frontier: do not globally jump back up.
- First visible control only: click the first visible expandable control, then rescan.
- Human-like visible click: dispatch pointer/mouse events at the visible element center, then fallback to `.click()`.
- Per-click heartbeat: emit `R45H_PROGRESS {event: "R45T_FIRST_VISIBLE_CLICK", ...}` after each single click.
- No batch clicking: keep `batch_candidate_clicking=false` by design.
- No hidden Facebook APIs, cookie/token extraction, browser profile parsing, or login automation.

Expected operator behaviour: the CMD should no longer sit silently after `R45J_AUTO_EXPAND_START`; it should print click heartbeats as it opens `View all ...`, `View hidden comments`, `View hidden replies`, and similar controls going downward.

## Self-test gate fix

The R45T first-visible implementation raises the local exhaustion ceiling to `Math.max(500, ...)` because it clicks exactly one visible expansion control per pass. The R45J self-test gate now accepts that R45T marker as preserving the R45R local-exhaust rule.
