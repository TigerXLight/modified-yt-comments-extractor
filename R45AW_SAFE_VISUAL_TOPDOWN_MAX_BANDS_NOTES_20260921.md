# R45AW safe visual top-down max-band separated comments capture

R45AW keeps the R45AT/R45AU/R45AV visible-page-only expansion path, but fixes the screenshot stage.

Fixes:

- Reset Facebook dialog/comment scrollers back to the top before visual cleanup/crop. This prevents the R45J/R45L crop from measuring comment nodes while the dialog is still scrolled near the bottom, which caused negative comment positions, collapsed narrow screenshots, and blank gaps.
- Skip one huge full-page PNG as the primary output. Very tall Chromium screenshots can blank/truncate. R45AW captures the separated comments column as maximum-height bands: `facebook_preserved_visual_comments_column_part_001_y00000000.png`, then part 002, etc.
- Preserve the old compatibility name `facebook_preserved_visual_comments_column.png` as a copy of part 001, while the numbered parts and ZIP are the authoritative evidence set.

Safety remains unchanged: visible page only; no hidden Graph/API scraping; no cookies/tokens; no profile parsing.
