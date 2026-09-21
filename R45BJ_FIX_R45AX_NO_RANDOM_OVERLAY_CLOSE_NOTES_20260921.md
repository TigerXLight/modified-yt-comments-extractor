# R45BJ fix R45AX no-random overlay close

R45BJ addresses the inspected local failure where the runner opened/handled a profile/DM overlay and then drifted away from the target story.

Changes:
- removes guessed coordinate fallback clicks inside `r45axCloseMessengerOverlays()`;
- makes profile-hover cleanup mouse-park-only, never clicking inside suspected profile cards;
- if a Messenger/chat overlay remains after explicit close attempts, blocks safely instead of continuing on a covered or drifting page;
- writes HTML, visible text, and viewport screenshot artifacts on that block state.

This is intentionally conservative: it should stop page drift and preserve evidence rather than guessing more clicks.
