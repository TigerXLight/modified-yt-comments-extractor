# R44M Reddit en.reddit.com primary signed-in link queue

R44M supersedes the R44L route priority.

The primary Reddit route is now:

1. Take normal/current Reddit links such as `https://www.reddit.com/...`.
2. Convert them to `https://en.reddit.com/...` capture URLs.
3. Require an operator-controlled signed-in Reddit session.
4. Open the main thread first, then branch/comment links in top-to-bottom order.
5. Capture visible DOM/screenshot only.
6. Feed captured pages into R44J comment-tree extraction and R44K reconciliation.

R44L remains useful as the secondary current-www fallback, but it is not the primary method.

Safety contract:

- no login automation
- no cookie or token extraction
- no browser profile file reading/copying/parsing
- no hidden Reddit API scraping
- no remote media downloads
- blocker-aware queue state rather than retry loops

The 2026-09-17 hierarchy file was used as the project-file reference for existing WebView2/minimal-CSS capability names, including the R42GZ independent fast media WebView2 lane and R42GY background WebView2 observer files.
