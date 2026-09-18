# R43W Bluesky Public Appview Import Lane

R43W adds a public Bluesky appview import lane above the R43V adapter.

It is intentionally narrow:

- uses public `app.bsky.feed.getAuthorFeed`-style appview JSON only when explicit live/public-network mode is requested;
- can also consume an injected/imported public appview feed payload for tests and offline validation;
- passes public `app.bsky.feed.defs#postView` objects into the R43V Bluesky adapter;
- lets R43V and R43U write the universal account/date/post/media ledger;
- records raw public appview payload receipts;
- does not download remote media;
- does not start a browser;
- does not copy WebView2/browser internals;
- does not extract cookies or tokens;
- does not automate login or bypass challenges.

This is the first real Bluesky public-account lane. It is not yet the visible-browser Bluesky capture lane.
