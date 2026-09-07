# R42CG Native WebView2 Source Role Editor

Based on R42CD/R42CC.

Fixes in this patch:

- Keeps the clean single-row native toolbar and WebView-below-toolbar layout.
- Keeps previous/next source arrow buttons removed.
- Keeps the compact source dropdown title/site/archive-prefix display.
- Adds URL-intake fallback from `self.source_resource_rows`, so a user TXT containing Original + Wayback + archive.ph can surface all three items in `source_navigation_urls`.
- Adds broader explicit URL-list fallback keys for future import paths.
- Does not automate CAPTCHA/challenge solving and does not treat challenge pages as evidence.

The important bug fixed here is that the source-role overlay payload could show only two navigation items even when the user's input TXT had three URLs. The missing `archive.ph` row was being lost before the native helper saw the payload.


R42CG adds human-chain source navigation: Original/Wayback/archive.ph rows from the same user TXT/link intake batch stay visible in the native toolbar even when an archive row is unchecked, challenge-blocked, or not evidence-ready. The archive target is navigation-only until article/source markers pass.


R42CG fixes R42CF archive omission: the native source dropdown is driven by the full latest human TXT/link intake batch plus current source rows, not only checked/evidence-ready source_navigation_urls. archive.ph/archive.today rows remain manual human-chain navigation-only targets until evidence markers pass.
