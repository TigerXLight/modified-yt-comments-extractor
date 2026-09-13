# R42GK Source Row to Evidence Bundle Plan Bridge Notes

Marker: `YTCE_R42GK_SOURCE_ROW_EVIDENCE_BUNDLE_PLAN_BRIDGE`

Status target: `PASS_R42GK_SOURCE_ROW_EVIDENCE_BUNDLE_PLAN_BRIDGE`

## Scope

R42GK adds an offline bridge from existing source-row-like inputs into deterministic evidence bundle plans. It does not fetch network content, launch a browser, execute WebView2/CDP, download media, run yt-dlp/JDownloader, execute extensions, submit archives, bypass challenges, harvest credentials, mutate source rows, assign source roles, alter counters, change no-jump behavior, or rewrite the review window.

## Implemented Contract

- `SourceRowInput` represents existing source rows, SourceCandidate-like rows, pasted URLs, and batch TXT rows.
- `EvidenceBundlePlan` describes planned evidence bundle paths, review-string index paths, source-role bridge path, media/comment/reply child paths, allowed method slots, blocked method slots, and guardrail status.
- URL inputs are sanitized through the R42GG sanitizer before entering `source_url`, `raw_url`, or `canonical_url`.
- Source family detection uses the R42GG family detector.
- Twitter/X single post, Twitter/X timeline, Metro/news article, Global Player/LBC public audio, and unknown/private review-only plans are generated as deterministic samples.
- R42GI media candidate ids are linked as planned child candidates only; they are not promoted into evidence.
- R42GJ review strings and source-role bridge semantics are reused so review-window/source-role matching remains compatible without assigning roles.

## Sample Plans

- BBCr4today status `2097217541416308845` maps to `bundle:twitter_x:post:2097217541416308845`.
- `examaddaorg` maps to a timeline/account export plan; the 6.7k record / 8.9 MB observation remains context only, not a hard limit.
- The Metro article maps to `bundle:news_websites:article:metro_seagull_eater_20260717`.
- The Global Player/LBC public audio fixture maps to `bundle:public_broadcast_catchup_audio:episode:2zGwFmzE7xNLAfiMVL5BMHmPeB` and preserves R42GH method metadata for `py -m yt_dlp`, native format `0`, native M4A preservation, and sidecars.
- Unknown/private/prohibited rows map to review-only plans with execution methods blocked.

## Guardrails

All source-role bridge records use `compatible_bridge_not_role_assignment` and `not_promoted_review_bridge_only`. Planned outputs are metadata/review bridges until a later marker-gated evidence capture/import provides accepted source material.
