# R44L Reddit normal-site link queue fallback

Adds a normal/current Reddit fallback plan for cases where a signed-in old/en Reddit
session is unavailable or undesirable.

## Method

- Open the current `www.reddit.com` main thread target first.
- Open each current Reddit branch/comment URL separately in the supplied
  top-to-bottom order.
- Preserve nested labels such as `2.1` immediately after their parent.
- Keep a resumable queue with `pending`, `captured`, `blocked`, and `skipped`.
- Use WebView2/minimal CSS rendering if available, but only for visible page
  rendering and capture.
- Stop on login gates, challenge pages, or network-security blocks.
- Feed captured DOM into R44J for comment tree extraction and R44K for
  reconciliation.

## Safety

No hidden Reddit API scraping, login automation, cookie/token extraction, browser
profile file reading/copying/parsing, WebView2 internals copying, or remote media
downloads.
