# R43E Universal Social Account Tracking Contract And Adapter Map

Marker: `YTCE_R43E_UNIVERSAL_SOCIAL_ACCOUNT_TRACKING_CONTRACT_ADAPTER_MAP`

R43E turns the Twitter/X account tracker into the first concrete platform adapter, not the permanent architecture.

## Contract

- Universal layer covers accounts, posts, reposts/reshares, quotes, replies, media, static screenshots, screenshot receipts, date folders, progress events, pause events, and recovery events.
- Twitter/X remains the first implemented adapter through R43D/R43B/R43A/R43C.
- Bluesky, Instagram, Facebook, Threads, Mastodon, TikTok, Reddit and future platforms are mapped as contract adapters so later patches reuse the same ledger/export model.
- WebView2 remains site rendering/observation only.
- Tracking, dedupe, date folder routing, account_record.md, media_index.json, screenshot receipts and manifests are local Python/app logic.
- No review-window/source-role lane dependency is introduced.
- No hidden API scraping, token/cookie extraction, challenge bypass, or remote media download is introduced.

## Files

- `profile_media_universal_social_account_tracking_r43e.py`
- `profile_media_universal_social_account_tracking_r43e_test.py`
- `main_universal_social_account_tracking_r43e_test.py`
- `R43E_UNIVERSAL_SOCIAL_ACCOUNT_TRACKING_CONTRACT_ADAPTER_MAP_NOTES_20260915.md`

## Main wiring

`main.py` registers `self.universal_social_account_tracking_registry_r43e` after the R43D Twitter/X export surface and passes the R43D surface as the current concrete Twitter/X adapter.
