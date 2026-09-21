# R45AR target-locked exact-label ordered exhaust

R45AQ fixed the real scroll container, but your run shows a new serious failure:
it navigated away to a Facebook user profile and still reported success.

R45AR fixes that class of bug:

1. Keeps the requested `story_fbid` as a hard target lock.
2. Checks the active URL before every click, after every click, and before success.
3. Fails with `R45AR_TARGET_SURFACE_LOST` instead of accepting a profile page.
4. Extracts exact labels such as `View all 10 replies`, not broad text rows such as
   `View all 10 replies Reply to Daniel James Broomhall`.
5. Clicks the exact label text rectangle.
6. Skips unsafe profile/name anchors.

No hidden Facebook API use, no cookie/token extraction, no profile parsing.
