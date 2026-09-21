# R45AU safe visual top-down skip-unsafe closeout

R45AU keeps the R45AT target/page/profile-navigation guard, but changes unsafe visual click points from fail-fast to skip-and-rescan.

Reason: the R45AT live run correctly blocked a bad point where the candidate text was reported as `View hidden replies`, but `elementFromPoint` showed the click would hit a Facebook profile/comment permalink anchor for a user name. That was a false-positive candidate, not a reason to stop the whole expansion.

Rules:
- visible page only
- no hidden Facebook APIs
- no cookies/tokens/profile parsing
- first safe visible expansion control is clicked
- unsafe candidates resolving to profile/comment anchors are logged as `R45AU_UNSAFE_CLICK_POINT_SKIPPED`
- the same viewport is rescanned immediately after a skip
- final screenshots require a full top-to-bottom audit pass with zero safe visible expansion controls
