# R44F Reddit No-Login Complete Comment Ordering

R44F adds the reliability layer requested after R44E: when the app Accounts/Keys metadata does not show a configured Reddit login, Reddit thread captures use a no-login route first.

Default no-login method:

1. Build an `en.reddit.com`/old Reddit thread URL with `sort=old`, `screen_view_count=1`, `limit=500`, and `ext-referrer=DIRECT`.
2. Preserve current-Reddit branch/comment URLs in the operator-visible top-to-bottom order. Labels such as `2.1` are kept in the branch queue.
3. Queue branch pages with `force-legacy-sct=1`.
4. Merge branch pages into the main thread by Reddit comment parent ids, avoiding duplicate anchor comments.
5. Store displayed Reddit net scores as visible score text. Reddit does not expose separate exact upvote/downvote totals in the visible page, so hidden scores remain hidden and numeric values are treated as displayed net scores only.
6. Write an indented `reddit_comment_tree_index.md` and `reddit_comment_tree_index.json` before passing the combined visible HTML into `R44D -> R43U`.

Safety boundaries remain unchanged: no cookie/token extraction, no browser profile copy, no login automation, no challenge bypass, no hidden platform API scraping, and no remote media downloads.
