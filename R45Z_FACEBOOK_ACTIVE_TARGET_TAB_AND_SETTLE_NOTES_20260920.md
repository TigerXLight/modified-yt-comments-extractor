# R45Z Facebook active target tab + expansion settle

Fixes two R45Y/R45X live issues:

1. Persistent Chromium can restore a crashed facebook.com feed tab in front of the fresh permalink tab. R45Z closes non-working restored tabs after the target permalink is opened and again before expansion, then brings the target tab to front.
2. Large explicit expand controls such as `View all 302 replies` can disappear immediately while Facebook streams replies in. R45Z waits for the click to settle before scrolling downward, so the pass remains an expand-comments-only pass but does not run away from a freshly opened thread.

Safety: visible browser/page interactions only. No hidden Facebook APIs, cookie/token extraction, browser profile parsing, WebView2 inspection, or login automation.
