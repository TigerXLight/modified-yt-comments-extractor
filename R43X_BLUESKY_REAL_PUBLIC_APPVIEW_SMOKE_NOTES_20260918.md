# R43X Bluesky real public appview smoke

Status target: `PASS_R43X_BLUESKY_REAL_PUBLIC_APPVIEW_SMOKE`

R43X adds an explicit public-network smoke harness for Bluesky public appview account import.

## Boundary

- Uses only `https://public.api.bsky.app/xrpc/app.bsky.feed.getAuthorFeed` through the R43W import lane.
- Requires `--public-network-enabled`, `--explicit-live-mode`, or `--live-mode` before a real public appview request is made.
- Writes raw public appview JSON payload receipts.
- Feeds `app.bsky.feed.defs#postView` rows through R43W -> R43V -> R43U.
- Does not start a browser, copy WebView2 internals, extract cookies/tokens, automate login, bypass challenges, or download remote media.

## Default validation

The module default report uses an injected fetcher. That proves the explicit-network code path and downstream ledger wiring without making an external request during ordinary unit validation.

## Real smoke

A real smoke is run with an explicit operator flag, for example:

```cmd
python profile_media_bluesky_real_public_appview_smoke_r43x.py --actor bsky.app --account-url https://bsky.app/profile/bsky.app --public-network-enabled --explicit-live-mode --max-items 3
```
