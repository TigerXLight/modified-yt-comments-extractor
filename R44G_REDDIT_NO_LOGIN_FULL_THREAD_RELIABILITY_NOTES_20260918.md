# R44G Reddit No-Login Full Thread Reliability

R44G hardens the Reddit method above R44F/R44D/R43U.

It freezes the no-login decision path for public Reddit thread capture:

- if Accounts/Keys metadata does not show a configured Reddit login, use the public no-login route;
- prefer old/en Reddit with `sort=old`, `screen_view_count=1`, `limit=500`, and `ext-referrer=DIRECT`;
- preserve operator/current-Reddit branch-comment URLs in visible top-to-bottom order;
- preserve nested branch labels such as `2.1` immediately after their parent label;
- merge branch pages by Reddit comment id and do not count duplicate anchor comments twice;
- rebuild indentation from parent ids and branch context;
- record displayed Reddit net scores separately, including negative and hidden scores;
- pass the combined visible HTML into R44F -> R44D -> R43U.

R44G does not read/copy browser profiles, cookies, tokens, cache, local storage, WebView2 internals, or Login Data. It does not automate login, bypass challenges, use hidden APIs, or download remote media. Real old-Reddit page capture only runs when `real_visible_smoke`, `public_network_enabled`, and `explicit_live_mode` are all explicitly set.
