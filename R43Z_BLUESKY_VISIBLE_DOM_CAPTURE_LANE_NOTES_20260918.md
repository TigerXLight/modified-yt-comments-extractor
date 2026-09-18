# R43Z Bluesky visible DOM capture lane

Status target: `PASS_R43Z_BLUESKY_VISIBLE_DOM_CAPTURE_LANE`

R43Z adds the broader visible-browser evidence lane for Bluesky without turning the patch into browser automation.

It covers in one patch:

- visible DOM post-card extraction for `bsky.app/profile/<handle>/post/<rkey>` links;
- article/card proximity binding for `img`, `video`, `source`, and `poster` media URLs;
- screenshot receipt materialization from caller-supplied visible screenshots, with fixture screenshots for validation;
- preservation of unbound account-level visible media candidates;
- delegation into the proven `R43V -> R43U` account/date/post/media ledger writer;
- main app registration and self-tests.

Boundary guarantees:

- R43Z does not start a browser.
- R43Z does not read or copy a browser profile, WebView2 directory, cookies, tokens, cache, local storage, or login databases.
- R43Z does not automate login or bypass challenges.
- R43Z does not perform hidden platform API scraping.
- R43Z does not download remote media bytes; media rows are metadata-only receipts.

R43Z is designed as the bridge between a future visible browser/WebView2 observer and the existing Bluesky ledger path. A visible browser caller can hand R43Z visible DOM HTML plus screenshots, and R43Z will turn them into the same universal ledger layout.
