# R43N Live Twitter/X Single Account Smoke Harness / Real Observation Receipt

Marker: `YTCE_R43N_LIVE_TWITTER_X_SINGLE_ACCOUNT_SMOKE_HARNESS_REAL_OBSERVATION_RECEIPT`

Pass status: `PASS_R43N_LIVE_TWITTER_X_SINGLE_ACCOUNT_SMOKE_HARNESS_REAL_OBSERVATION_RECEIPT`

Truthful blocked statuses:

- `BLOCKED_PLACEHOLDER_TARGET_URL`
- `BLOCKED_NEEDS_VISIBLE_SESSION`
- `BLOCKED_WEBVIEW2_RUNTIME_UNAVAILABLE`
- `BLOCKED_NO_LIVE_OBSERVATIONS`
- `NEEDS_PATCH_R43N_LIVE_SMOKE_PATH_NOT_CONNECTED`

## Purpose

R43N adds a user-runnable smoke harness for one Twitter/X account or post. It is not another control-plane surface. It prepares and, when explicitly requested, runs the existing route:

`R43L -> R43J/R43K -> R43I -> R43H -> R43G -> R43F -> R43E -> R43D -> R43B -> R42GZ -> R42GY/R42GV -> R43A/R43C`

## Default Validation Mode

Automated validation does not start WebView2, does not access the network, and does not fake success from fixture/sample/probe output. The normal CLI/report run returns `BLOCKED_NEEDS_VISIBLE_SESSION` with an empty bad-check list when no visible human session is requested.

Placeholder/example targets such as `PUT_HANDLE_HERE`, `PUT_STATUS_ID_HERE`, or `https://x.com/example` return `BLOCKED_PLACEHOLDER_TARGET_URL`. The `--run-visible-live` flag alone is never proof of observation and cannot turn a placeholder target into PASS.

## Real Smoke Mode

The generated command runner and module CLI can be run with `--run-visible-live` after the user chooses a public Twitter/X account or post URL. A real PASS requires non-fixture observation evidence from the live/session-backed R42GZ boundary.

PASS requires all of the following:

- The target URL is not placeholder/example/test-only.
- Explicit live mode and visible-session requirements are true.
- The R42GZ boundary is invoked.
- At least one non-fixture observation evidence record exists.
- At least one observed post/media/screenshot/materialization count is greater than zero.
- Concrete live observation output paths exist and are outside fixture/sample/probe/synthetic folders.
- The receipt contains observed output paths, not only prepared route-chain metadata.

Exact boundary prepared:

`profile_media_independent_fast_media_webview2_lane_r42gz.IndependentFastMediaWebView2LaneBackendR42GZ.observe_media`

The R42GZ lane is configured for explicit live visible-session smoke use (`live=True`, `headless=False`, `fixture_mode=False`) when the harness executes a real smoke.

## Guardrails

- No hidden API scraping.
- No cookie or token extraction.
- No login automation.
- No CAPTCHA/challenge/paywall/access-control bypass.
- Human login/challenge handling is allowed only by visible human action.
- No remote media downloads during automated tests.
- No source-role or review-window side effects.
- No YouTube capture engine changes.
- Fixture/sample/probe output cannot count as a live PASS.
- R43O diagnostic files must stay in R43O fields only; when observed counts are zero, R43N clears non-fixture evidence and live_observation_paths.
- R43N forwards `--browser-user-data-dir` to R43O; diagnostic files from zero-observation attempts are recorded as diagnostics only and do not count as live evidence.
