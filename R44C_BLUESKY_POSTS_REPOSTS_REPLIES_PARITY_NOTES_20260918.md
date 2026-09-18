# R44C Bluesky posts/reposts and posts/replies parity

R44C adds Bluesky timeline-mode parity with the Twitter/X account capture layer.

Supported user-facing scopes:

- `posts_and_reposts` / `posts_and_retweets`: profile timeline capture; visible text, media, screenshots and repost evidence are preserved through R44A -> R43Z -> R43V -> R43U.
- `posts_and_replies`: replies timeline capture; visible text, media, screenshots and reply evidence are preserved through the same ledger.

Public appview path:

- `posts_and_reposts` maps to `app.bsky.feed.getAuthorFeed` with `filter=posts_and_author_threads`; feed `reasonRepost` metadata is preserved and normalized to `record_type=repost_or_reshare`.
- `posts_and_replies` maps to `filter=posts_with_replies`; app.bsky `record.reply` metadata is preserved and normalized to `record_type=reply`.

Visible-browser path:

- R44A now computes a Bluesky navigation URL for the requested feed mode.
- Post URLs are preserved exactly.
- Profile URLs in `posts_and_replies` mode navigate to `/profile/<handle>/replies`.
- Profile URLs in `posts_and_reposts` mode navigate to `/profile/<handle>`.
- R43Z records the visible feed mode and carries text/media/screenshot receipts into the same R43V/R43U ledger.

Safety boundaries remain unchanged: no cookie/token extraction, no browser-profile copy, no hidden API scraping, no challenge bypass, and no remote media downloads.
