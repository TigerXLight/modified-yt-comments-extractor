# R45J Facebook preserved visual screenshot runner

R45J fixes the R45I screenshot mismatch.

R45I intentionally generated a static print-clean comment-card evidence page. That is useful as a complete text evidence index, but it is not the original Facebook visual layout.

R45J uses the same bounded visible expansion path as R45H, then performs a post-expansion visual cleanup of the live Facebook-rendered DOM. It preserves the Facebook comment bubbles, avatars, nesting, visible reaction counts, and Like/Reply metadata, while removing surrounding Facebook chrome, modal headers, close buttons, and composer/reply input boxes.

Safety contract:
- no hidden Facebook API scraping
- no cookie or token extraction
- no browser-profile file reading/copying/parsing
- no login automation
- visible page expansion only, followed by screenshot cleanup


## R45J screenshot default fix

- Fixes live crash after operator pause caused by stale `args.screenshot` reference.
- Full preserved-visual screenshot is now captured by default whenever screenshots are not disabled.
- `--tile-screenshots` still adds tiled captures.
- `--no-screenshots` remains the opt-out.


## R45J visual blank-page fix

The first preserved-visual live run passed text comparison and wrote files, but the browser preview was blank. The receipt still showed the selected dialog had hundreds of thousands of text characters, so the failure was visual cleanup, not expansion. The fix keeps the original Facebook-rendered comments DOM in place and hides/crops surrounding chrome, instead of cloning the dialog and replacing `document.body`. This preserves the Facebook bubble/avatar/reaction layout for screenshots.
