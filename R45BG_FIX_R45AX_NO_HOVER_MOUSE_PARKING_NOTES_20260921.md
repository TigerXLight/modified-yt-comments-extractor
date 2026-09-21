# R45BG fix: no-hover mouse parking and profile-card closure

The R45BF/R45BE runner can leave the Playwright mouse resting over Facebook names while the internal comments scroller moves. Facebook then opens profile/name hover cards, which can cover comments and slow the visible-page pass.

R45BG changes:
- parks the mouse at a neutral viewport corner immediately after every expansion click;
- parks the mouse after internal scroller movement and top-audit resets;
- detects and closes profile/name hover cards separately from Messenger/DM overlays;
- logs `R45AX_PROFILE_HOVER_CARD_CLOSED`;
- keeps click timing comparison logs: `click_elapsed_ms` and `timing_delta`;
- preserves R45BE target-drift guard, R45BD Messenger guard, R45BC dead-click skip, R45BB full-audit restarts, and R45BA real-scroller selection.

Visible-page only. No hidden Facebook APIs, no cookies/tokens, and no browser-profile parsing/copying.
