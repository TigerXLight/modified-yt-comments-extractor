# R45AT safe visual top-down Facebook expansion

R45AT fixes the R45AS/R45AQ profile-navigation regression.

The failure pattern was visible in live logs: expansion labels were detected, but a click could resolve to a Facebook profile/comment permalink such as `/dbroomhall?comment_id=...`, leaving the target story. R45AT treats any profile/profile-comment path as unsafe unless it is the requested story/permalink surface.

Rules:
- visible-page-only expansion;
- no hidden Facebook APIs;
- no cookies/tokens/profile parsing;
- install a capture-phase blocker for profile/profile-comment navigation;
- before each click, verify the click point does not resolve to a profile/profile-comment anchor;
- require a full top-to-bottom zero-control audit before screenshots.
