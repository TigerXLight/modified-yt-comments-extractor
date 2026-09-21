# R45AV Safe visual top-down + separated comments-box screenshot

R45AV keeps the R45AU visible-page-only expansion model, including target-story guard, profile/comment-permalink navigation blocking, unsafe-click skipping, and the full top-to-bottom zero-visible-controls audit.

The new closeout step is post-expansion visual separation:

1. after the full audit passes, it applies the older working R45J/R45L preserved visual cleanup;
2. it hides the surrounding Facebook webpage/sidebar/modal chrome and comment composer;
3. it crops away pre-comment post/media surfaces;
4. it keeps the original Facebook-rendered comment bubbles, avatars, nesting, reactions, Like/Reply metadata;
5. it writes `facebook_preserved_visual_comments_column.png`;
6. it also writes `facebook_preserved_visual_comments_only_full_page.png` and optional separated tile screenshots when `--tile-screenshots` is used.

No hidden Facebook/Graph APIs, cookie/token extraction, login automation, browser profile parsing, or WebView2 storage inspection is used.
