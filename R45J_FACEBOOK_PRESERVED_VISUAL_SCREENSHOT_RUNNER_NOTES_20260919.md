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
