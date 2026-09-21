# R45AS visual top-down audit closeout

Purpose: finish the Facebook comment expansion problem without trusting the broken all-loaded count.

Rule:
1. Open the target post.
2. Start at the top of the active comments scroller.
3. Click the first visible expansion control.
4. Rescan the same viewport before moving down.
5. Continue downward as Facebook loads more comments.
6. At the bottom, restart a top-to-bottom audit pass.
7. Screenshot only after a full visual top-to-bottom pass finds zero remaining expand controls.

This is visible-page-only. It does not use hidden Facebook APIs, cookies, tokens, or browser profile parsing.
