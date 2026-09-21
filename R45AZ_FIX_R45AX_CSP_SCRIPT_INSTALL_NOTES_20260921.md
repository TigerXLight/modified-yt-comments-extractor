# R45AZ – Fix R45AX CSP-safe script installation

This closeout fixes the live failure:

- `Page.add_script_tag: Executing inline script violates Content Security Policy`

R45AY replaced the earlier `page.evaluate(...)` injection with `page.add_script_tag(...)`, but Facebook's CSP blocks inline script tags. R45AZ keeps the fixed regex/self-test work and installs the visible-page helper functions through a Playwright `page.evaluate` function expression instead, then exports the helper functions onto `window`.

The runner remains visible-page only:

- no hidden Facebook APIs
- no cookies/tokens extraction
- no browser profile file parsing/copying
- no WebView2 storage inspection
- no remote media downloads

Expected live behaviour:

1. lock to the target story
2. use the active comments modal scroller
3. open safe visible expansion labels
4. gate completion on progress text such as `657 of 715` reaching the total
5. flatten the loaded Facebook comments modal into a comments-only page with no internal scroll box
6. screenshot maximum-height comments-column bands
