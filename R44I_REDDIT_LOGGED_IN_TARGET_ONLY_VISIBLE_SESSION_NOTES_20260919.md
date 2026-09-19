# R44I Reddit logged-in target-only visible session

R44I records the working Reddit capture method discovered during the EdSheeran thread test.

## Working route

- Use an operator-controlled logged-in Chromium profile.
- Launch Chromium directly with the exact old/en Reddit target URL as a browser command-line argument.
- Do not call Playwright `page.goto()` for Reddit in direct-launch mode.
- After the operator pause, capture the currently visible page only.
- Do not bulk-open branch URLs.
- Sanitize with Python-side DOM filtering rather than browser-side JavaScript injection.
- Send the sanitized DOM and screenshot to `R44D -> R43U`.

## Tested target

`https://en.reddit.com/r/EdSheeran/comments/1whbgzk/eds_got_a_show_in_4_days_no_band_no_openers_what/?sort=old&screen_view_count=1&limit=500&ext-referrer=DIRECT`

The successful direct-launch smoke produced:

- `PASS_R44I_REDDIT_LOGGED_IN_TARGET_ONLY_VISIBLE_SESSION`
- final page URL equal to the old/en Reddit target URL
- `record_count=349`
- `visible_record_count=349`
- `media_count=3`
- `PASS_R44D_REDDIT_VISIBLE_DOM_CAPTURE_ADAPTER`
- `PASS_R43U_UNIVERSAL_SOCIAL_ACCOUNT_LEDGER_CONTRACT_BASELINE`

## Safety contract

- The browser may use an explicitly supplied `--user-data-dir`, but the tool does not inspect, copy, zip, or parse cookies, tokens, Login Data, Local State, Local Storage, cache, or browser profile files.
- No login automation.
- No credential entry by the tool.
- No hidden Reddit API scraping.
- No challenge bypass.
- No remote media downloads.
- The route is target-only and does not loop branch pages.

## Caveat

Old Reddit displayed `351 comments`; R44I captured `349` visible records. Treat this as the reliable live route, but run a later comment-ID comparison before claiming exact complete parity.
