# R42GF Twitter/X Adapter Closeout

Status: `IMPLEMENTED`, `VALIDATED_CURRENT_METHOD`, `REVIEW_REQUIRED`, `SIDE_EFFECT_FREE_VALIDATION`

R42GF closes out Twitter/X as a specialist source-adapter family, not as a generic article lane.

## Current methods recognised

- `source_adapters.py` recognises `x.com` and `twitter.com` as `twitter_x`.
- `source_twitter_compact_row.py` preserves the compact Post/Thread source row.
- `twitter_route_strategy.py` maps public status, profile/timeline, media timeline, list workaround, article, search, likes, and bookmarks routes.
- `twitter_browser_capture_strategy.py` remains the read-only browser/session response planning layer.
- `twitter_media_backend.py` keeps public status/direct-media work on the shared media backend / JDownloader API3128 plan, not a separate Twitter-only downloader.
- `twitter_rate_limit_policy.py` preserves rate-limit and auth/access boundary stops.
- `twitter_status_evidence_extractor.py`, screenshot preservation, profile/media provenance, and V77C live-output closeout remain evidence/provenance lanes.
- `capture_twitter_exporter_review_flow.py` remains the safe local exporter flow: source review -> queue draft -> manifest/report -> action-log/provenance receipt.

## Boundary

R42GF does not launch a browser, hit X/Twitter, use the official X API, read cookies/tokens/browser profiles, download media, take screenshots, submit archives, crawl, bypass CAPTCHA/login/rate limits/access controls, or perform X write actions.

Protected/login-limited material remains `requires_access` / `blocked` / `review_required`. Full account export parity is not claimed.

## Matrix update

`profile_media_source_family_matrix_r42gc.py` is updated so the `twitter_x` family is no longer described as merely `baseline_exists_not_closed`. It is now `validated_current_method` for the specialist Twitter/X routes, while completed evidence remains receipt-gated.
