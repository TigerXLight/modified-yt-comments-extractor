# R45BD fix: Messenger/DM overlay guard and click timing delta logs

R45BC correctly detected dead clicks, but the latest run opened a Facebook Messenger/DM overlay while trying to expand comments.

R45BD changes:
- detects Messenger/chat overlays after every expansion click;
- closes the overlay, marks that exact candidate key inert, and logs `R45AX_MESSENGER_OVERLAY_BLOCKED`;
- closes any newly opened tab/page and logs `R45AX_UNEXPECTED_PAGE_CLOSED`;
- records `click_elapsed_ms` and a `timing_delta` object for every click so reply/replies interactions can be compared before/after;
- timing delta includes scrollHeight, scrollTop, visible control count, visible count map, and progress before/after.

Still visible-page only. No hidden Facebook APIs, no cookies/tokens, no browser-profile parsing/copying.
