# R43P Live Twitter/X Runner Output Promotion Notes

Marker: `YTCE_R43P_LIVE_TWITTER_X_RUNNER_OUTPUT_PROMOTION`

Status target: `PASS_R43P_LIVE_TWITTER_X_RUNNER_OUTPUT_PROMOTION`

R43P is a read-only promotion/accounting pass for local files already written by the visible Twitter/X runner path. It does not start WebView2, CefSharp, network capture, hidden API scraping, login automation, media downloads, source-role routing, review-window routing, or YouTube capture code.

The repair addresses the R43N/R43O gap where a real visible run wrote non-fixture R42GZ outputs but the R43O/R43N receipts still reported zero observed posts/media/screenshots. R43P scans the runner output directory for local artifacts such as `screenshot.png`, `rendered_dom_snapshot.html`, `visible_browser_media_observations.json`, `visible_browser_media_observations.ndjson`, R42GT `media_index.json`, R42GT `media_index.ndjson`, `post.json`, and `timeline.ndjson`.

Network files such as `network_events.jsonl`, `network_response_bodies.jsonl`, and `api_pages.jsonl` are recorded, but network-only evidence is not enough for a live smoke PASS. PASS still requires real post, media, screenshot, DOM/materialization, or receipt evidence.

R43P also normalizes markdown-wrapped Twitter/X URLs at the R43N/R43O boundary so machine URL fields remain plain URLs such as `https://x.com/examaddaorg`, not Markdown links.

Integrated receipt fields added to R43O and R43N include:

- `r43p_runner_output_promotion_invoked`
- `r43p_runner_output_promotion_status`
- `r43p_runner_output_promotion_receipt_path`
- `promoted_observed_post_count`
- `promoted_observed_media_count`
- `promoted_observed_screenshot_count`
- `promoted_network_event_count`
- `promoted_api_page_count`
- `promoted_response_body_count`
- `promoted_live_observation_paths`
- `promoted_non_fixture_observation_evidence`

R43O also records `why_observed_count_was_zero_before_promotion` when direct R42GZ counters were zero but file promotion found real local evidence.
