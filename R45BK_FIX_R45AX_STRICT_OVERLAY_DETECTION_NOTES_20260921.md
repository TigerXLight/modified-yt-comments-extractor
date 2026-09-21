# R45BK — strict overlay detection

Fixes the R45BJ false block where ordinary expanded comment bubbles inside the
Facebook comments modal were classified as Messenger/profile overlays.

Root cause:
- `r45axMessengerOverlayState()` scanned generic `div` nodes.
- It used a loose `Aa\s*` branch, so ordinary comment text/names could match.
- It did not ignore descendants of the active comments scroller.
- `r45axProfileHoverOverlayState()` had the same scroller-descendant problem.

Changes:
- Ignore `el === scroller` and `scroller.contains(el)` in both overlay detectors.
- Remove loose Messenger `Aa\s*` text matching.
- Require strong chat signatures or chat input plus chat chrome.
- Require profile hover signals plus actual profile buttons.
- Preserve R45BJ no random coordinate close, R45BI expected-total gate, and target drift guard.

Safety:
- Visible page only.
- No hidden Facebook APIs.
- No cookies/tokens/profile parsing.
- No guessed coordinate clicks added.
