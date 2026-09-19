# R44J Reddit comment tree extraction + indentation

R44J adds a comment-tree extraction layer for Reddit thread captures.

It records the working capture strategy discovered in R44I:

- logged-in, operator-controlled Chrome/Chromium profile;
- direct-launch old/en Reddit target URL;
- no Playwright `page.goto()` after operator pause;
- target URL only; no bulk branch loop;
- visible page DOM/screenshot capture only;
- no cookie/token/Login Data/Local State/local storage/cache/profile-file copying or parsing.

It also preserves the fallback method for users who are not signed into Reddit:

- try current `www.reddit.com` visible target-only capture;
- stop on login gates or network-security blocks;
- use saved HTML, copied visible text, screenshots, or other manual evidence if public capture blocks;
- never invent missing comments when Reddit's displayed count exceeds visible/recoverable nodes.

Large-thread policy:

- `limit=500` is not a completeness guarantee for 1k+ comment threads;
- record reported vs recovered counts;
- write a resumable branch/more-comments queue;
- process one target/branch page per operator-confirmed run to reduce Reddit security/rate-limit risk;
- preserve branch labels/order and nested labels such as `2.1` after `2`.

Score policy:

Reddit exposes displayed net score text, not exact separate upvote and downvote totals. R44J preserves hidden, zero, positive, and negative net-score text without inferring exact vote totals.
