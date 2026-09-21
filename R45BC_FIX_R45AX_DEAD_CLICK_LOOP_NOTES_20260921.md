# R45BC fix: dead-click skip for inert Facebook expansion controls

This fixes the R45BB run pattern where the same visible `View hidden replies` candidate is clicked again and again at the same scroll position and coordinates.

Observed symptom from the user log:
- at scrollTop around 12160, visible labels remain `View hidden replies` / `View hidden replies`;
- the same coordinate is clicked repeatedly;
- scrollHeight, progress, and visible counts do not change, so the run loops instead of continuing.

R45BC changes:
- each expansion candidate now carries a stable `key`;
- the runner records pre-click and post-click signatures: scrollHeight, scrollTop, visible count, counts, and progress;
- if the same candidate remains visible after two no-progress clicks, it is marked inert with `r45axAddSkipKey(key)`;
- future scans skip only that exact inert candidate and continue with the next candidate or scroll down;
- logs `R45AX_DEAD_CLICK_KEY_SKIPPED` when this happens.

Still visible-page only. No Facebook hidden APIs, no cookies/tokens, no browser-profile parsing/copying.
