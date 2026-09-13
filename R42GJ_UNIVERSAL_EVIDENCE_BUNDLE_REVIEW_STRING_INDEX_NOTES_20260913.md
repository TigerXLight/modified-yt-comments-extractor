# R42GJ Universal Evidence Bundle + Review String Index Notes

Status target: `PASS_R42GJ_UNIVERSAL_EVIDENCE_BUNDLE_REVIEW_STRING_INDEX`

R42GJ adds an offline evidence bundle and review-string bridge contract. It does not fetch the network, launch a browser, run yt-dlp, run JDownloader, execute extensions, bypass challenges, harvest credentials, mutate source roles, alter counters, or rewrite the review window.

## Implemented

- Universal evidence record schema for posts/statuses, timelines/account exports, articles, episodes/audio items, archive/manual/local evidence shapes, and child/comment paths.
- Evidence bundle manifest schema for shared export folders, records index, review strings, media index, progress events, audit log, and source-role bridge.
- Review string index schema mapping strings to evidence records, media candidates, and source-role bridge records.
- Source-role bridge schema that remains compatibility data only, not a role assignment engine.
- Folder layouts for Twitter/X single post, Twitter/X timeline/account export, news article, and public audio/Global Player bundles.
- Sample Twitter/X single post card for `https://x.com/BBCr4today/status/2097217541416308845`.
- The BBCr4today single-post fixture uses the supplied quote/body text and is marked as a manual receipt/local exporter import contract sample.
- Sample Twitter/X timeline/account bundle for `https://x.com/examaddaorg` with the R42GF/R42GG dynamic benchmark preserved as context, not a hard-coded limit.
- Sample Metro/news article bundle.
- Sample Global Player/LBC audio bundle preserving the R42GH yt-dlp Python-module/native-M4A method metadata.
- R42GI media candidate IDs linked into evidence records without promotion.
- Plain URL hygiene for machine URL fields and URL-like review strings.

## Guardrails

- Metadata-only, review-required, blocked, login-limited, private, or manual-receipt-needed records are not promoted to accepted evidence.
- Source-role bridge records set `role_hint = none` and `promotion_status = not_promoted_review_bridge_only`.
- Existing review-window/source-role/no-jump/counter behavior is untouched.

## Verification Environment Note

If `py -3.11` resolves to the WindowsApps stub and returns `Access is denied`, use `C:\Users\fahad\AppData\Local\Programs\Python\Python311\python.exe` and record that in verification output.
