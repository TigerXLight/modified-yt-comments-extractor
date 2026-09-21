# R45BE fix: target drift and scroll-stall guard

R45BD added Messenger overlay protection, but the latest run still navigated the active tab away from the original permalink into a Facebook page/profile surface.

R45BE changes:
- broadens same-tab Facebook href blocking so `/pages/`, `/profile.php`, `/people/`, username/page links, and other non-story Facebook links are not considered safe expansion controls;
- checks the target story before every scan;
- checks the target story immediately after every click;
- if the active tab no longer contains the expected story id, writes a receipt and stops with `BLOCKED_TARGET_DRIFT` / `BLOCKED_TARGET_DRIFT_AFTER_CLICK` instead of continuing on the wrong page;
- adds `R45AX_SCROLL_STALLED_BLOCKED` so repeated no-movement scrolls cannot loop for hundreds of steps on a wrong/non-modal page;
- preserves timing deltas, dead-click skipping, Messenger overlay closure, and full zero-control audit behavior.

Still visible-page only. No hidden Facebook APIs, no cookies/tokens, no browser-profile parsing/copying.
