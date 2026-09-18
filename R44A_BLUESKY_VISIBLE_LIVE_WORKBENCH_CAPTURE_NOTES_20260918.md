# R44A Bluesky visible live workbench capture

Status target: `PASS_R44A_BLUESKY_VISIBLE_LIVE_WORKBENCH_CAPTURE`

R44A adds the visible-live browser/workbench caller above the R43Z visible DOM lane. It gives the universal route a Bluesky visible capture path:

`R43L -> R43J -> R43I -> R43H -> R43G -> R43F -> R43E -> R44A -> R43Z -> R43V -> R43U`

## Scope

- Accept caller-supplied visible DOM/screenshot evidence.
- Accept an injected visible browser runner for tests and future GUI handoff.
- Optionally launch a clean visible Playwright browser only when explicit live visible flags and `allow_external_visible_browser_capture` are supplied.
- Persist visible DOM HTML, screenshot receipts, and a redacted browser snapshot receipt.
- Delegate DOM/media/screenshot materialization to R43Z, then R43V and R43U.

## Safety boundaries

- R44A does not read or copy browser profiles.
- R44A does not read or copy WebView2 user-data directories, cache, cookies, local storage, login databases, or tokens.
- R44A does not automate login or bypass challenges.
- R44A does not perform hidden platform API scraping.
- R44A does not download remote media bytes; media remains metadata-only receipt evidence through R43Z/R43U.

## Validation

The self-test uses an injected browser runner, so validation does not perform real network access. The direct CLI can perform a real public visible browser smoke only when explicitly asked with live flags and `--allow-external-visible-browser-capture`.
