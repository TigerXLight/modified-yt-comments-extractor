# R45AQ container-aware ordered exhaust

R45AP exposed the real failure: it found the first remaining control
(`View all 302 replies`) but `window.scrollTo()` did not move the active
Facebook comments surface. `scrollY` stayed at 0, so it looped without ever
clicking.

R45AQ keeps the simple policy but fixes the scroller:

1. Count visible pending controls.
2. Click the first/topmost visible pending control.
3. Rescan the same viewport before scrolling.
4. When a loaded control is below the viewport, scroll its nearest Facebook
   scroll container, not just `window`.
5. Accept success only when all loaded expansion controls count to zero.
6. If the first remaining control cannot be revealed, fail fast with
   `R45AQ_BLOCKED_REMAINING_EXPAND_CONTROLS`.

It also cleans accidental Markdown-style target URLs:
`[https://...](https://...)` -> `https://...`.

No hidden Facebook API use, no cookie/token extraction, no profile parsing.
