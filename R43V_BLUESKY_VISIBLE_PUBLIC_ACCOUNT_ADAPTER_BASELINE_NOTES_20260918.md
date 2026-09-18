# R43V — Bluesky Visible/Public Account Adapter Baseline

## Purpose

R43V adds the first Bluesky adapter above the R43U universal social account ledger contract. It maps imported/visible/public Bluesky post-view style data into the same account/date/post/media folder contract already proven for Twitter/X by R43T/R43A/R43R.

## Scope

- Adds `profile_media_bluesky_visible_account_adapter_r43v.py`.
- Adds direct tests and a `main.py` registration test.
- Routes Bluesky fixture/account exports through R43E/R43F instead of leaving Bluesky as a pending platform.
- Uses the R43U universal ledger writer.
- Keeps Bluesky native fields nested under `platform_specific.bluesky`.

## Bluesky mapping baseline

- Profile URL: `https://bsky.app/profile/<handle-or-did>`
- Post URL: `https://bsky.app/profile/<handle-or-did>/post/<rkey>`
- AT URI: `at://<did>/app.bsky.feed.post/<rkey>`
- Native identity: `did`, `handle`, `at_uri`, `cid`, `rkey`
- Media/embed types: images, video playlist/thumbnail, external cards, record/recordWithMedia.

## Boundaries

R43V does not start a browser, use WebView2, copy browser internals, read cookies/tokens, automate login, bypass challenges, perform hidden platform API scraping, or download remote media. It is an adapter/normalizer plus universal-ledger writer integration. Live Bluesky visible-browser capture is for the next step.

## Validation target

- R43V fixture adapter report: PASS.
- R43E routes Bluesky fixture mode to R43V with a PASS downstream status.
- R43F routes Bluesky fixture mode through R43E/R43V.
- Existing Twitter/X R43A/R43T/R43R tests remain green.
