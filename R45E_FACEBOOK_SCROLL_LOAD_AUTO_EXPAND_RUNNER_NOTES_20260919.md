# R45E Facebook scroll-load auto-expand runner

R45E extends R45D after the real Facebook run showed the remaining gap: R45D clicked visible expansion controls, but comments further down the Facebook comments box were not loaded until the page/comments container was scrolled.

R45E keeps the same safety contract and adds scroll-load sweeps:

1. keep the logged-in visible Facebook page alive;
2. inject CSS-only comments focus mode;
3. click visible expansion controls;
4. scroll both the page and large visible scrollable containers;
5. re-scan and click newly loaded controls after each scroll;
6. capture DOM, visible text, full screenshot, tiled screenshots, and comparison receipt.

Safety: no hidden Facebook/Graph API scraping, no login automation, no cookies/tokens, no browser-profile parsing/copying, no remote media downloads.
