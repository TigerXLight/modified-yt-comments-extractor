# R43S Twitter/X Live Profile Lock Preflight Notes

R43S adds a narrow live-profile preflight before the R43O visible-session binding constructs the R42GZ lane. It checks the requested Chromium user-data-dir for existence, directory/write access, obvious Chromium singleton lock files, and matching running Chromium command lines.

The preflight does not read cookies, tokens, browser databases, local storage, cache contents, or profile secrets. Process diagnostics are redacted to PID, process name, match status, and the matched target profile only.

If preflight blocks, R43O writes `profile_preflight_summary.json` and returns the precise profile blocker without launching Playwright or starting WebView2. R43N and R43D bubble the blocker through `profile_preflight_status` and `profile_preflight_summary`, and the normal R43L app-shell receipt exposes those fields via `live_evidence_summary`.

If preflight passes, the existing R43Q/R43R path remains unchanged: R43D invokes R43N, R43N invokes R43O, R43O invokes R42GZ/R43P, and R43D invokes R43R only when promoted non-fixture live evidence exists.

R43S does not add a route layer, duplicate the R43A ledger writer, perform login automation, bypass challenges, extract cookies or tokens, download remote media, or change the YouTube capture engine.
