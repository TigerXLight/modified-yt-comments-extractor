# R43O Live Twitter/X Visible Session Binding Notes

R43O binds the R43N smoke harness to the existing visible/session-backed Twitter/X browser media observation path instead of adding another abstract control plane.

The concrete boundary is:

`profile_media_independent_fast_media_webview2_lane_r42gz.build_independent_fast_media_webview2_lane_r42gz -> twitter_browser_capture_runner.run_twitter_browser_capture`

R43O writes a visible-session binding request, receipt, progress log, blocker file, observation-path index, summary, and report. It records whether a browser/session was launched or attached, whether navigation was attempted, whether the observer started, the observation store path, files written, observed post/media/screenshot counts, and materialization receipt count.

R43N now calls R43O for real-looking `--run-visible-live` targets and includes the R43O fields in `live_smoke_observation_receipt.json`:

- `r43o_visible_session_binding_invoked`
- `r43o_visible_session_binding_status`
- `visible_session_launched_or_attached`
- `visible_navigation_attempted`
- `observer_started`
- `observation_store_path`
- `visible_session_binding_receipt_path`
- `visible_session_binding_blocker_reason`
- `visible_session_binding_files_written`

Placeholder targets are still blocked before any R43O binding call. The placeholder detector now includes `REAL_HANDLE` and `REAL_STATUS_ID` in addition to `PUT_HANDLE_HERE`, `PUT_STATUS_ID_HERE`, and example/test/sample placeholders.

Automated tests use injected runners and must not start WebView2, CefSharp/CEF, browsers, network activity, downloads, hidden APIs, cookie/token extraction, login automation, challenge bypass, source-role checks, review-window loops, or YouTube capture engine changes.

R43O does not make fake PASS possible. PASS requires non-fixture observation files and observed counts. If the visible/session path is attempted but writes no observations, the truthful status is `BLOCKED_NO_LIVE_OBSERVATIONS`; if no visible session can be used, the truthful status is `BLOCKED_NEEDS_VISIBLE_SESSION` or `BLOCKED_WEBVIEW2_RUNTIME_UNAVAILABLE`.
- R43O/R43N support `--browser-user-data-dir` so the smoke can use the existing signed-in `YTCE X Test Chromium` profile without extracting cookies or tokens.
- R43P now promotes already-written R42GZ/twitter browser runner artifacts into R43O receipt counts. R43O records the R43P promotion receipt path, promoted post/media/screenshot/network counts, promoted live observation paths, and why direct counters were zero before promotion when applicable. This remains read-only receipt accounting and does not alter the visible browser runner or capture engine behavior.
