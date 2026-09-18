# R44B Bluesky real Windows visible-browser smoke

R44B is the final live smoke wrapper above the R44A -> R43Z -> R43V -> R43U Bluesky visible-browser stack.

It adds a real-smoke harness that can launch a clean visible Playwright Chromium session through R44A only when the operator explicitly supplies the real-smoke/live flags. It records rendered HTML, screenshot receipts, downstream ledger output, and safety side-effect flags.

## Safety boundary

R44B does not read or copy browser profiles, WebView2 user-data directories, cookies, tokens, local storage, cache files, login databases, or remote media bytes. It does not automate login or bypass challenge screens. Media rows remain metadata-only unless later explicitly downloaded by a separate user-controlled path.

## Validation modes

- Default/report mode uses an injected fake visible browser runner and performs no real browser or network activity.
- Real visible smoke mode uses `--real-visible-smoke` and delegates to R44A with explicit live flags.
- If the live page returns posts and screenshots but no media rows are present in the rendered sample, the smoke can still pass with a warning; the R43Z fixture path continues to prove media binding when media is visible.

## Route chain

`R44B -> R44A -> R43Z -> R43V -> R43U`
