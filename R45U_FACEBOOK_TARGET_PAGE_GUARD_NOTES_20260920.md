# R45U Facebook target page guard — 2026-09-20

Fixes a live-run safety regression where the browser could be on the generic Facebook home/feed page while a specific permalink target URL had been requested.

R45U adds a guard after the operator login/pre-expand pause:

- if the current browser URL already matches the requested target identity, expansion proceeds;
- otherwise the runner reopens the sanitized target URL once;
- if the browser is still not on the requested target, the run is blocked before any visible-page expansion clicks;
- the receipt records `target_page_guard`;
- the guard prevents expanding unrelated feed posts.

Safety boundaries remain unchanged: no hidden Facebook APIs, no token/cookie extraction, no browser-profile parsing, no login automation.
