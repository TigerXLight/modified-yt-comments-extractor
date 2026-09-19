# R45G Facebook modal hidden replies runner

R45G builds on R45F after live testing showed Facebook controls labelled **View hidden replies** remained visible in the post modal.

## Method

- Keep the logged-in visible Chromium/WebView2 Facebook modal.
- Keep CSS-only comment focus mode; do not delete the comment DOM.
- Prefer modal/dialog scrollers.
- Click visible controls:
  - View hidden comments
  - View hidden replies
  - View 1 reply
  - View all replies
  - View more replies
  - See more
- Scroll modal/comment containers between click sweeps.
- Capture visible text/DOM/screenshots after loading.

## Safety

No hidden Facebook API scraping, no Graph endpoints, no cookie/token extraction, no profile file parsing/copying, no login automation, and no remote media downloads.
