# R43T Twitter/X Fast Media To Post Ledger Binding Notes

Marker: `YTCE_R43T_TWITTER_X_FAST_MEDIA_TO_POST_LEDGER_BINDING`

R43T binds already-captured Twitter/X fast media observations into the existing
R43R -> R43A account ledger flow. It does not add a new route, does not start a
browser, and does not download remote media.

Implemented behavior:

- Loads R42GV visible browser media observations JSON/NDJSON.
- Loads R42GV segment NDJSON receipts.
- Loads R42GT media index JSON/NDJSON.
- Loads `media_inventory.json` from the browser runner.
- Binds media to extracted article/post records by status ID, canonical post URL,
  or article DOM media URL.
- Preserves loose account-level media as unbound candidates instead of attaching
  them to every timeline post.
- Feeds bound media into R43A as `TwitterXAccountMediaItemR43A` rows so R43A
  remains responsible for local-byte copying and remote URL receipt writing.
- Preserves binding status, binding reason, source observation marker, byte
  status, and metadata-only/no-download flags in post JSON and media indexes.
- Applies the R43C screenshot receipt gate after R43A writes post folders, keeping
  session screenshot fallback labels truthful.

Safety boundaries:

- No hidden API scraping.
- No cookie or token extraction.
- No login automation.
- No CAPTCHA, challenge, paywall, or access-control bypass.
- No remote Twitter/X media downloads.
- No YouTube capture engine behavior changes.
