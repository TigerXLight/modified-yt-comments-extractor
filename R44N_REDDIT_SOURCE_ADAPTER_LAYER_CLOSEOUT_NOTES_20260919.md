
# R44N Reddit source adapter layer closeout — 2026-09-19

R44N closes the Reddit source-adapter layer after R44D through R44M.

## Closed route order

Primary Reddit route:

1. Convert normal/current Reddit URLs to `https://en.reddit.com/` capture URLs.
2. Require an operator-controlled signed-in Reddit account/session.
3. Open the main target URL first.
4. Open branch/comment links one at a time in supplied top-to-bottom order.
5. Use the existing WebView2/minimal-CSS lane where useful for faster visible rendering.
6. Feed captured pages into R44J comment-tree extraction.
7. Reconcile counts with R44K.
8. Enrich/align with R43U ledger outputs where needed.

Secondary fallback:

- R44L current `www.reddit.com` queue remains available only as secondary fallback when the signed-in `en.reddit.com` route cannot be used.
- It must stop on login gates, account-required pages, network-security blocks, or challenges.
- It must write blocked receipts and preserve queue state; it must not bulk-loop or bypass platform blocks.

## Safety closeout

The adapter layer is closed with these side-effect boundaries:

- No hidden Reddit API scraping.
- No login automation.
- No credential entry by the tool.
- No cookie/token extraction.
- No browser profile file copying/parsing.
- No WebView2/browser storage inspection.
- No remote media downloading.

## Large thread closeout

For 1k+ comment threads, `limit=500` is not a completeness guarantee. The source adapter must use the queue, record reported-vs-recovered gaps, and never invent hidden/missing comments.
